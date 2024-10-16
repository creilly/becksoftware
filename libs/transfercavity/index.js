// beckhttp protocol constants
var JSON_TYPE = 'application/json';
var COMMAND = 'command';
var PARAMETERS = 'parameters';
var ERROR = '_error';
var NOHEATER = 1347;

// scan div element id
var SCANPLOT = 'scan-plot';
var DFPLOT = 'df-plot';

// channel parameters
var HENE = 'hene';
var IR = 'ir';
var DF = 'df';
var inputchannels = [HENE,IR];
var channelcolors = {
	[HENE]:'#BB0000',[IR]:'#0000BB'
};

// scan x axis (constant)
var scanx = null;
var scanlength;
var scanX = [];
var fitscanx = [];
var fitscanX = [];
var fitscann = 300;
var fullscanlen = 3001; // hardcoded magic number !

// scan display params
var scancanvas;
var scancontext;
var scanheight;
var scanwidth;
var markersize = 1.5;
var linewidth = 0.5;
var margin = 10; // pixels

// fitting contants
var Vo = 4.0;
var modfreq = 511.0; // hz
var sampling_rate = 200e3; // samps per second
var VMAX = 'vmax';
var VMIN = 'vmin';
var DELTAV = 'deltav';
var SIGMAV = 'sigmav';
var VP = 'vp';
var VPP = 'vpp';
var MUV = 'muv';
var DF = 'df';
var PHIF = 'phif';

var fitparamindices = [VMAX, VMIN, DELTAV, SIGMAV, VP, VPP, MUV, DF, PHIF];

// df display params
var dfcanvas;
var dfheight;
var dfwidth;
var dfhistory = 300;
var scanindex = -1;
var dfs = [];
var SCANINDEX = 0;
var DELTAF = 1;
var setpoint = null;

// debugging
var timer = Date.now();
var gscan;
var npoints = 3000;
// var dfN = 10;
// var dfn = 0;

function get_interval() {
	var now = Date.now();
	var then = timer;
	var interval = now - then;
	timer = now;
	return interval;
}

function send_command(command, parameters, cb) {
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {	
	if (this.readyState == 4) {
		cb(JSON.parse(xhttp.responseText));
	}
	};
	xhttp.open('POST', '', true);
	xhttp.setRequestHeader('Content-Type',JSON_TYPE);
	var data = {};
	data[COMMAND] = command;
	data[PARAMETERS] = parameters;
	xhttp.send(JSON.stringify(data));
}

function on_setpoint(_setpoint) {
	setpoint = _setpoint;
}

var indicatorindex = 0;
indicators = [
	['get error','error-state-indicator',{},-1,null],
	['get heating','heater-state-indicator',{},-1,heater_cb],
	['get heater voltage','heater-voltage-indicator',{},4,heater_cb],
	['get scanning','scan-state-indicator',{},-1,null],
	['get fitting','hene-fit-state-indicator',{channel:HENE},-1,null],
	['get fitting','ir-fit-state-indicator',{channel:IR},-1,null],
	['get scan index','scan-index',{},-1,null],
	['get center voltage','hene-peak',{channel:HENE},4,null],
	['get center voltage','ir-peak',{channel:IR},4,null],
	// ['get offset','peak-offset-indicator',{},4,null],
	['get setpoint','lock-setpoint-indicator',{},2,on_setpoint],
	['get locking','lock-state-indicator',{},-1,null],
	['get lock output','lock-output',{},4,null],
	['get modulation frequency','mod-freq-indicator',{},2,on_modfreq]
];

function heater_cb(value) {
	if (
		typeof value == 'object' 
		&& 
		ERROR in value 
	) {
		if (value[ERROR][0] == NOHEATER) {
			for (var id of ['heater-state','heater-voltage']) {
				document.getElementById(id).style.display = 'none';
			}
		}
		else {
			console.log('error',value);
		}
	}		
}

function update_cb(id,precision,cb) {
	return function (value) {	
	if (cb != null) {
		cb(value);
	}
	if (precision > 0) {
		value = parseFloat(value).toFixed(precision);
	}
	document.getElementById(id).innerHTML = value;
	}
}

function update_indicators() {
	indicator = indicators[indicatorindex];
	var indicatorcommand = indicator[0];
	var indicatorid = indicator[1];
	var indicatorparams = indicator[2];
	var indicatorprecision = indicator[3];
	var indicatorcb = indicator[4];
	send_command(
		indicatorcommand,
		indicatorparams,
		update_cb(indicatorid,indicatorprecision,indicatorcb)
	);
	setTimeout(
		update_indicators,
		25
	);
	indicatorindex += 1;
	if (indicatorindex == indicators.length) {
		indicatorindex = 0;
	}
}

function decode_floats(b64s) {
	var bs = window.atob(b64s);
	var bsl = bs.length;
	var ba = new Uint8Array(bsl);
	for (var i = 0; i < bsl; i++) {
		ba[i] = bs.charCodeAt(i);
	}
	var fa = new Float32Array(ba.buffer);
	return fa
}

function distort_v(v,vp,vpp) {
	return Vo + 1 * (v - Vo) + vp * (v - Vo)**2 + vpp * (v - Vo)**3;
}

function transmission(index,v,vmax,vmin,deltav,sigmav,vp,vpp,muv,df,phif) {
	var v = distort_v(v,vp,vpp);
	var muv = muv + df / 100.0 * Math.sin(
		2. * Math.PI * modfreq / sampling_rate * fullscanlen / fitscann * index - phif / 180.0 * Math.PI
	);
	var b = 1/Math.sin(Math.PI/2*sigmav/deltav)**2 - 2;
	var a = ( 1 + 1 / b ) * ( vmax - vmin );
	var c = vmin - a / ( 1 + b );
	var t = a / ( 1 + b * Math.sin(Math.PI * ( v - muv ) / deltav)**2 ) + c;	
	return t;
}

function fit(params) {
	var n = 0;	
	return fitscanx.map(
		function (x) {
			y = transmission(
				...[n,x].concat(
					fitparamindices.map(
						function (index) {
							return params[index];
						}
					)
				)
			);
			n += 1;
			return y;
		}
	);
}

function transform(z,zmin,zmax,Zmin,Zmax) {
	return Zmin + (z-zmin)/(zmax-zmin)*(Zmax-Zmin);
}

function update_plot_lims(channel,ys) {
	var miny = Math.min(...ys);
	var maxy = Math.max(...ys);
	document.getElementById(
	{
		[HENE]:'hene-min-act',
		[IR]:'ir-min-act',
		[DF]:'df-min-act'
	}[channel]
	).innerHTML = miny.toFixed(4);
	document.getElementById(
	{
		[HENE]:'hene-max-act',
		[IR]:'ir-max-act',
		[DF]:'df-max-act'
	}[channel]
	).innerHTML = maxy.toFixed(4);
	var ymin;
	var ymax;
	if (
	document.getElementById(
		{
		[HENE]:'hene-autoscale',
		[IR]:'ir-autoscale',
		[DF]:'df-autoscale'
		}[channel]
	).checked
	) {
	ymin = miny;
	ymax = maxy;
	}
	else {
	ymin = document.getElementById(
		{
		[HENE]:'hene-min-con',
		[IR]:'ir-min-con',
		[DF]:'df-min-con'
		}[channel]
	).value;			
	ymax = document.getElementById(
		{
		[HENE]:'hene-max-con',
		[IR]:'ir-max-con',
		[DF]:'df-max-con'
		}[channel]
	).value;
	}
	return [ymin,ymax];
}

function initialize_plot(canvas,context,width,height) {
	canvas.width = 0;
	canvas.width = width;
	context.lineWidth = linewidth;
	context.strokeStyle = '#000000';
	context.beginPath();
	context.rect(0,0,width,height);
	context.stroke();
}

function update_scan() {
	send_command(
	'get scan decimated',
	{},
	function (scan) {
		if (document.getElementById('scan-pause').checked) {
			setTimeout(update_scan,0);
			return;
		}
		initialize_plot(scancanvas,scancontext,scanwidth,scanheight);
		for (var channel in scan) {		
		var scanarr = scan[channel];
		var scandata = scanarr[0];
		if (scandata != null) {		    
			var scany = decode_floats(scandata);
			var ylims = update_plot_lims(channel,scany);
			var ymin = ylims[0];
			var ymax = ylims[1];		    
			var scanY = scany.map(
			function (y) {
				return transform(
				y,ymin,ymax,scanheight-margin,margin
				);
			}
			);
		}
		else {
			continue;
		}
		var params = scanarr[1];
		if (params != null) {
			scancontext.lineWidth = linewidth;
			scancontext.strokeStyle = channelcolors[channel];
			var fitX = fitscanX;
			var fitY = fit(params).map(
			function (y) {
				return transform(
				y,ymin,ymax,scanheight-margin,margin
				);
			}
			);
			scancontext.beginPath();
			scancontext.moveTo(fitX[0],fitY[0])
			n = 1;
			while (n < fitscann) {
			scancontext.lineTo(fitX[n],fitY[n]);
			n += 1;
			}
			scancontext.stroke();
		}
		var n = 0
		scancontext.fillStyle = channelcolors[channel];
		while (n < scanlength) {
			var X = scanX[n];
			var Y = scanY[n];			
			scancontext.fillRect(
			X-markersize/2,Y-markersize/2,markersize,markersize
			);
			n += 1;
		}
		}
		setTimeout(
			update_scan,
			0
		);
	}
	);
}
function on_modfreq(modfreqp) {			
	modfreq = modfreqp;
}
function update_df() {
	send_command(
		'get samples',
		{
			maxindex: scanindex
		},
		function (samples) {
			if (samples.length == 0) {
			send_command(
				'get scan index',
				{},
				function (_scanindex) {
				if (_scanindex < scanindex) {
					scanindex = -1;
				}
				setTimeout(			    
					update_df,
					100
				);
				}
			);
			return;
			}
			for (var sample of samples) {
				scanindex = sample[SCANINDEX];
				dfs.splice(0,0,sample[DELTAF]);
			}
			while (dfs.length > dfhistory) {
				dfs.pop();
			}
			if (dfs.length) {
			var errorsignal = dfs[0];
			if (errorsignal != null) {
				errorsignal = errorsignal.toFixed(2);
			}
			document.getElementById('error-signal').innerHTML = errorsignal;		
			}	    
			if (document.getElementById('df-pause').checked) {
			setTimeout(
				update_df,
				100
			);
			return;
			}
			var ylims = update_plot_lims(DF,dfs);
			var ymin = ylims[0];
			var ymax = ylims[1];
			if (setpoint != null) {
				dfcontext.strokeStyle = '#CC8800';
				dfcontext.lineWidth = linewidth;
				dfcontext.beginPath();
				var spXl = transform(0,0,dfhistory,margin,dfwidth-margin);
				var spXr = transform(dfhistory,0,dfhistory,margin,dfwidth-margin);
				var spY = transform(setpoint,ymin,ymax,dfheight-margin,margin);
				dfcontext.moveTo(spXl,spY);
				dfcontext.lineTo(spXr,spY);
				dfcontext.stroke()
			}
			var y;
			var x;
			var X;
			var Y;
			var moving = true;
			initialize_plot(dfcanvas,dfcontext,dfwidth,dfheight);
			dfcontext.strokeStyle = '#008800';
			dfcontext.beginPath();
			for (var index in dfs) {
				x = index;		
				y = dfs[index];
				if (y == null) {
					moving = true;
					continue;
				}
				X = transform(x,0,dfhistory,margin,dfwidth-margin);
				Y = transform(y,ymin,ymax,dfheight-margin,margin);
				if (moving) {
					dfcontext.moveTo(X,Y);
				}
				else {
					dfcontext.lineTo(X,Y);
				}
				moving = false;
			}
			dfcontext.stroke();
			setTimeout(
				update_df,
				100
			);
		}
	)
}

function on_load() {
	document.getElementById('error-clear').onclick = function () {
		send_command(
			'clear error',
			{},
			function () {}
		);
	};
	document.getElementById('heater-state-submit').onclick = function () {
		send_command(
			'set heating',
			{
			heating:document.getElementById('heater-state-control').checked
			},
			function () {}
		);
	};
	document.getElementById('heater-voltage-submit').onclick = function () {
	send_command(
		'set heater voltage',
		{
		voltage:parseFloat(
			document.getElementById('heater-voltage-control').value
		)
		},
		function () {}
	);
	};
	document.getElementById('scan-state-submit').onclick = function () {
	send_command(
		'set scanning',
		{
		scanning:document.getElementById('scan-state-control').checked
		},
		function () {}
	);
	};
	document.getElementById('hene-fit-state-submit').onclick = function () {
	send_command(
		'set fitting',
		{
		channel:HENE,
		fitting:document.getElementById('hene-fit-state-control').checked
		},
		function () {}
	);
	};
	document.getElementById('ir-fit-state-submit').onclick = function () {
	send_command(
		'set fitting',
		{
		channel:IR,
		fitting:document.getElementById('ir-fit-state-control').checked
		},
		function () {}
	);
	};
	// document.getElementById('peak-offset-submit').onclick = function () {
	// send_command(
	// 	'set offset',
	// 	{
	// 	offset: parseFloat(
	// 		document.getElementById('peak-offset-control').value
	// 	)
	// 	},
	// 	function () {}
	// );
	// };
	document.getElementById('lock-state-submit').onclick = function () {
	send_command(
		'set locking',
		{
		locking:document.getElementById('lock-state-control').checked
		},
		function () {}
	);
	};
	document.getElementById('lock-setpoint-submit').onclick = function () {
	send_command(
		'set setpoint',
		{
		setpoint: parseFloat(
			document.getElementById('lock-setpoint-control').value
		)
		},
		function () {}
	);
	};
	document.getElementById('zero-offset').onclick = function () {
	send_command(
		'zero offset',
		{},
		function () {}
	);
	};
	
	scancanvas = document.getElementById(SCANPLOT);
	scancontext = scancanvas.getContext('2d');
	scanheight = scancanvas.height;
	scanwidth = scancanvas.width;

	dfcanvas = document.getElementById(DFPLOT);
	dfcontext = dfcanvas.getContext('2d');
	dfheight = dfcanvas.height;
	dfwidth = dfcanvas.width;
	
	update_indicators();
	send_command(
		'get x decimated',
		{},
		function (xs64) {
			scanx = decode_floats(xs64);
			scanlength = scanx.length;
			var xmin = scanx[0];
			var xmax = scanx[scanx.length-1];
			scanx.forEach(
			function (x) {
				scanX.push(transform(x,xmin,xmax,margin,scanwidth-margin));
			}
			)
			n = 0
			var x = xmin;
			var dx = (xmax-xmin)/(fitscann-1);
			while (n < fitscann) {
			fitscanx.push(x);
			fitscanX.push(transform(x,xmin,xmax,margin,scanwidth-margin));
			x += dx;
			n += 1;
			}
			update_scan();
		}	
	)
	update_df();	
}

function on_resize() {
}
window.onload = on_load;
window.onresize = on_resize;

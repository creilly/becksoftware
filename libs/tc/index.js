var canvas, cw, ch;
var channel;
var cb = 0.025;

var vs, vs_scaled;

var HENE = 'hene';
var IR = 'ir';
var channels = [HENE,IR];

var SCAN = 'scan';
var FIT = 'fit';

var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

var laserd = {
    topo:'down',argos:'up'
};

function send_command(command, parameters, cb = null) {
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {	
        if (this.readyState == 4) {       
            var response = JSON.parse(xhttp.responseText);
            if (
                typeof yourVariable === 'object' &&
                !Array.isArray(yourVariable) &&
                yourVariable !== null &&
                '_error' in response
            ) {
                console.log('error!',response['_error'])
            }
            else{
                if (cb !== null) {
                    cb(response)
                };
            }
        }
	};
	xhttp.open('POST', '', true);
	xhttp.setRequestHeader('Content-Type',JSON_TYPE);
	var data = {};
	data[COMMAND] = command;
	data[PARAMETERS] = parameters;
	xhttp.send(JSON.stringify(data));
}

function update_plot(delay,control) {
    var xs = times.map((t) => (cb + (1-2*cb) * (t - tmin) / (tmax-tmin)) * canvas.width);
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,cw,ch);   
    ctx.strokeStyle = 'black';
    ctx.moveTo(cb*cw,cb*ch);
    ctx.lineTo(cb*cw,(1-cb)*ch);
    ctx.lineTo((1-cb)*cw,(1-cb)*ch);
    ctx.lineTo((1-cb)*cw,cb*ch);
    ctx.lineTo(cb*cw,cb*ch);
    ctx.stroke();
    for (var i = 0; i < 2; i++) {
        var zs = i ? delays : controls;
        var zmin = i ? dmin : cmin;
        var zmax = i ? dmax : cmax;
        var color = i ? 'red' : 'blue';
        var ys = zs.map((z) => (cb + (1-2*cb) * (zmax - z) / (zmax-zmin)) * canvas.height);        
        ctx.strokeStyle = color;
        ctx.beginPath();        
        ctx.moveTo(xs[0],ys[0]);
        for (var j = 0; j < ys.length; j++) {
            ctx.lineTo(xs[j],ys[j]);
        }
        ctx.stroke();
    }
}

function on_scan(scanl) {
    var scanindex = scanl[0];
    var scand = scanl[1];
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,cw,ch);    
    for (var i = 0; i < channels.length; i++) {
        var channelname = channels[i];
        var cdata = scand[channelname];        
        var scandata = decode_floats(cdata[SCAN]).map((z) => 1e3*z); // to millivolts        
        var xs = vs_scaled;
        var zminmeas = Math.min(...scandata);        
        document.getElementById(
            channelname + '-min-value'
        ).innerHTML = zminmeas.toFixed(1);
        var zmaxmeas = Math.max(...scandata);
        document.getElementById(
            channelname + '-max-value'
        ).innerHTML = zmaxmeas.toFixed(1);
        var zmin = (
            document.getElementById(
                channelname + '-min-autoscale'
            ).checked ? zminmeas : parseFloat(
                document.getElementById(
                    channelname + '-min-input'
                ).value
            )
        );
        var zmax = (
            document.getElementById(
                channelname + '-max-autoscale'
            ).checked ? zmaxmeas : parseFloat(
                document.getElementById(
                    channelname + '-max-input'
                ).value
            )
        );
        var ys = scandata.map(
            (z) => (cb + (1-2*cb) * (zmax-z) / (zmax - zmin))*ch
        );
        ctx.beginPath();
        ctx.strokeStyle = {
            hene:'red',ir:'blue'
        }[channelname];
        ctx.moveTo(xs[0],ys[0]);
        for (var j = 0; j < ys.length; j++) {
            ctx.lineTo(xs[j],ys[j]);
        }
        ctx.stroke();
    }
    setTimeout(loop,40);
}

function loop() {
    send_command(
        'get scan', {direction:channel,decimated:true}, on_scan
    );
}

function get_channel() {
    var laser = window.location.href.split('&')[1];
    document.getElementById('laser-label').innerHTML = laser;
    return laserd[laser]
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

function on_vs(b64vs) {    
    vs = decode_floats(b64vs);
    console.log(vs);
    var vmin = Math.min(...vs);
    var vmax = Math.max(...vs);
    vs_scaled = vs.map(
        (v) => (cb + (1-2*cb) * (v - vmin) / (vmax - vmin))*cw
    );
    loop();
}

function get_vs() {
    send_command(
        'get x',{direction:channel,decimated:true},
        on_vs
    )
}

function on_load() {
    canvas = document.getElementById('canvas');
    cw = canvas.width;
    ch = canvas.height;
    channel = get_channel();
    get_vs();    
}

window.onload = on_load;
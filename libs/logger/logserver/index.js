// beckhttp protocol constants
var JSON_TYPE = 'application/json';
var COMMAND = 'command';
var PARAMETERS = 'parameters';

var groups_select;
var years_select;
var months_select;
var days_select;

var start_check;
var start_time;
var end_check;
var end_time;
var delta_time;

var update_button;

var show_markers;

var plot_div;

var log_data;
var log_channels;
var log_units;
var log_group;
var log_date;
var log_timer = null;

var dummy_date = '2000-01-01';

var width = 1200; // pixels
var height = 800; // pixels

var colors = [
    '#a04040',
    '#40a040',
    '#4040a0',
    '#808040',
    '#804080',
    '#408080'
];

var symbols = [
    'circle','square','diamond'
];

var dashes = [
    'solid','dot'
];

var markersize = 4.0;

function send_command(command, parameters, cb, hook = (x) => x) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {	
	if (this.readyState == 4) {
	    cb(JSON.parse(hook(xhttp.responseText)));
	}
    };
    xhttp.open('POST', '', true);
    xhttp.setRequestHeader('Content-Type',JSON_TYPE);
    var data = {};
    data[COMMAND] = command;
    data[PARAMETERS] = parameters;
    xhttp.send(JSON.stringify(data));
}

function add_options(select,options,autoupdate) {
    while (select.options.length) {
	select.remove(0);
    }
    if (!options.length) {return;}
    options.forEach(
	function (optiontext) {
	    var option = document.createElement('option');
	    option.text = optiontext;
	    select.add(option);
	}
    );
    select.value = options.pop();
    if (autoupdate) {
	select.onchange();
    }
}

function configure_onchange(select_from,select_to,command,params,autoupdate) {
    select_from.onchange = function () {
	_params = {};
	for (var param in params) {
	    var select = params[param]
	    _params[param] = get_selected_option(select);
	}
	send_command(
	    command,
	    _params,
	    function (options) {
		add_options(select_to,options,autoupdate);
	    }
	)
    }
}

function get_selected_option(select) {
    return select.options[select.selectedIndex].text;
}

function get_date() {
    var year = get_selected_option(years_select);
    var month = get_selected_option(months_select);
    var day = get_selected_option(days_select);
    return [year,month,day].join('-');
}

function get_group() {
    return get_selected_option(groups_select);
}

function get_log() {
    log_group = get_group();
    log_date = get_date();
    if (log_timer != null) {
	clearTimeout(log_timer);
	log_timer = null;
    }
    var metadata_params = {
	group: log_group,
	date: log_date
    }
    send_command(
	'get-channels',
	metadata_params,
	(channels) => {
	    log_channels = channels;
	    send_command(
		'get-units',
		metadata_params,
		(units) => {
		    log_units = units;
		    params = get_data_params();
		    send_command(
			'get-data',
			params,
			(data) => update_plot(data,false),
			data_hook
		    );
		}
	    )
	}
    );
}

function update_plot(data,extend) {
    var ys = [];
    for (var i = 1; i < data[0].length; i++){
	ys.push([]);
    }
    var x = [];
    data.forEach(
	(line) => {
	    x.push(dummy_date + 'T' + line[0]);
	    for (var i = 1; i < line.length; i++) {
		ys[i-1].push(line[i]);
	    }
	}
    );
    if (extend) {
	Plotly.extendTraces(
	    plot_div,
	    {
		y:ys,
		x:ys.map((y) => x)
	    },
	    [...Array(ys.length).keys()]
	)
    }
    else {
	plots = []
	for (var i in ys) {
	    var color = colors[i % colors.length];
	    var symbol = symbols[Math.floor(i/colors.length)];
	    var dash = dashes[Math.floor(i/colors.length)];
	    var mode = markers_check.checked ? 'markers+lines' : 'lines';
	    plots.push(
		{
		    x: x,
		    y: ys[i],
		    mode: mode,
		    name: log_channels[i],
		    marker: {
			symbol: symbol,
			color: color,
			size: markersize
		    },
		    line: {
			dash: dash,
			color: color
		    }
		}
	    )
	}
	Plotly.newPlot(
	    plot_div,
	    plots,
	    {
		title: log_group + ': ' + log_date,
		xaxis: {
		    tickformat: '%H:%M:%S'
		},
		yaxis: {
		    title: log_units,
		    type: 'log',
		    autorange: true
		},
		width: width,
		height: height
	    }
	);
    }
    if (new Date().toISOString().split('T')[0] == log_date) {
	log_timer = setTimeout(
	    () => {
		update_data(log_group,log_date,x[x.length-1].split('T')[1]);
	    },
	    1000 * get_delta()
	);
    }
}

function get_data_params() {
    params = {};
    params['group'] = log_group;
    params['date'] = log_date;
    if (start_check.checked) {
	var start = start_time.value;
    }
    else {
	var start = null;
    }
    params['start'] = start;
    if (end_check.checked) {
	var end = end_time.value;
    }
    else {
	var end = null;
    }
    params['end'] = end;
    params['delta'] = get_delta();
    return params
}

function get_delta() {
    return parseFloat(delta_time.value);
}

function data_hook(s) {
    return s.replace(/\bNaN\b/g, "null");
}

function update_data(group,date,start) {
    if (group == log_group && date == log_date) {
	params = get_data_params();
	params['start'] = start;
	send_command(
	    'get-data',
	    params,
	    (data) => update_plot(data,true),
	    data_hook
	);
    }
}

function on_load() {
    groups_select = document.getElementById('groups');
    years_select = document.getElementById('years');
    months_select = document.getElementById('months');
    days_select = document.getElementById('days');
    start_check = document.getElementById('start-enabled');
    start_time = document.getElementById('start-time');
    end_check = document.getElementById('end-enabled');
    end_time = document.getElementById('end-time');
    delta_time = document.getElementById('delta');
    update_button = document.getElementById('update');
    markers_check = document.getElementById('show-markers');
    plot_div = document.getElementById('plot');

    update_button.onclick = get_log;
    
    params = [
	[
	    groups_select,
	    years_select,
	    'get-years',
	    {
		'group':groups_select
	    },true	    
	], [
	    years_select,
	    months_select,
	    'get-months',
	    {
		'group':groups_select,
		'year':years_select
	    },true
	], [
	    months_select,
	    days_select,
	    'get-days',
	    {
		'group':groups_select,
		'year':years_select,
		'month':months_select,
	    },false
	]	
    ]
    params.forEach((arglist) => {configure_onchange(...arglist);});
    send_command('get-groups',{},(groups) => {add_options(groups_select,groups,true);});
}

function on_resize() {
}
window.onload = on_load;
window.onresize = on_resize;

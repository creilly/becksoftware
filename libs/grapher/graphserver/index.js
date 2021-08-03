var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

var ROOT = '_data';
var ROOTID = 'root';
var ROOTTOKEN = '_tree';

var XID = 'x-axis';
var YID = 'y-axis';

var PLOTID = 'plot';

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

function format_path_list(path) {
    return [ROOTTOKEN].concat(path).join('/');
    // return '/' + [ROOT].concat(path).join('/');
}

function parse_path_string(path_string) {
    return path_string.split('/').slice(1);
    // var full_path_list = path_string.split('/');
    // return full_path_list.slice(2,full_path_list.length);
}

function add_leaves(parent,folder) {    
    send_command(
	'get-dir',
	{folder:folder},
	add_leaves_cb(parent,folder)
    );
}

function add_leaves_cb(parent,root_folder) {
    return function (data) {
	var files = data[0];
	var folders = data[1]; 
	folders.forEach(
	    function (folder) {
		var new_folder = root_folder.concat(folder);
		var li = document.createElement('li');
		var sp = document.createElement('sp');
		var cb = document.createElement('input');
		var bu = document.createElement('button');
		var ul = document.createElement('ul');

		parent.appendChild(li);
		li.appendChild(sp);
		li.appendChild(ul);
		sp.appendChild(cb);
		sp.appendChild(bu);
		bu.append(folder);
		bu.classList.add('folder');
		
		li.setAttribute('id',format_path_list(new_folder));
		
		cb.setAttribute('type','checkbox');
		cb.setAttribute('tabindex',-1);
		// cb.checked = true;
		cb.onchange = function () {
		    var li = this.parentElement.parentElement;
		    var ul = li.querySelector('ul');
		    var path = parse_path_string(li.getAttribute('id'));
		    if (cb.checked) {
			add_leaves(ul,path);
		    }
		    else {
			while (ul.lastElementChild) {
			    ul.removeChild(ul.lastElementChild);
			}
		    }
		}

		bu.onclick = function () {cb.click();};	

		// add_leaves(ul,new_folder);
	    }
	);
	files.forEach(
	    function (file) {
		var li = document.createElement('li');
		var bu = document.createElement('button');

		parent.appendChild(li);
		li.appendChild(bu);

		li.setAttribute('id',format_path_list(root_folder.concat(file)));
		bu.innerText = file;
		bu.classList.add('dataset');
		bu.onclick = function () {
		    var path = parse_path_string(bu.parentElement.getAttribute('id'));
		    set_dataset(path);
		};
	    }
	);
    }
}
function get_dataset(path,cb) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {	
	if (this.readyState == 4) {
	    var rawdata = xhttp.responseText;
	    var lines = rawdata.split('\n');
	    var header = lines[0];
	    var fields = header.slice(2,header.length).split('\t');
	    columns = [];
	    for (var i = 0; i < fields.length; i++) {
		columns.push([]);
	    }
	    lines.slice(1,lines.length).forEach(
		function (line) {
		    rawfloats = line.split('\t');
		    for (var i = 0; i < fields.length; i++) {
			columns[i].push(parseFloat(rawfloats[i]));
		    }
		}
	    )
	    cb(fields,columns)
	}
    };
    xhttp.open('GET', format_path_list(path), true);
    xhttp.send();
}

function update_plot() {
    var selects = [XID,YID].map(
	function (id) {
	    return document.getElementById(id).querySelector('select');
	}
    )

    var indices = selects.map(
	function (select) {
	    return select.selectedIndex
	}
    )

    var X = 0;
    var Y = 1;
    
    var columns = [X,Y].map(
	function (axis) {
	    return global_columns[indices[axis]];
	}
    )

    var labels = [X,Y].map(
	function (axis) {
	    return selects[axis].options[indices[axis]].value;
	}
    )

    var data = [
	{
	    x: columns[X],
	    y: columns[Y],
	    mode: 'markers',
	    type: 'scatter'
	}
    ];
    
    var width = window.innerWidth;
    var height = window.innerHeight;
    var scale = .75;

    var layout = {
	xaxis: {
	    title: labels[X]
	},
	yaxis: {
	    title: labels[Y]
	},
	title: global_path.join(' : '),
	width: scale*width,
	height: scale*height
    };

    Plotly.newPlot(
	PLOTID,
	data,
	layout
    );
}
var global_fields;
var global_columns;
var global_path;
var global_timer = null;
var global_time;
function set_dataset(path) {
    if (global_timer != null) {
	clearTimeout(global_timer);	
    }
    global_time = new Date().getTime();
    send_command(
	'get-fields',
	{path:path},
	function (fields) {
	    [XID,YID].forEach(
		function (id) {
		    var td = document.getElementById(id);
		    
		    while (td.lastElementChild) {
			td.removeChild(td.lastElementChild);
		    }
		    
		    var select = document.createElement('select')

		    td.appendChild(select);
		    fields.forEach(
			function(field) {
			    var option = document.createElement('option');
			    option.text = field;
			    select.add(option);
			}
		    )
		    if (id == XID) {
			select.selectedIndex = 0;
		    }
		    if (id == YID) {
			select.selectedIndex = 1;
		    }
		    select.onchange = update_plot;
		}
	    );
	    global_fields = fields;
	    _update_dataset();
	}
    );
    global_path = path;
}

function _update_dataset() {
    send_command(
	'get-data',
	{path:global_path},
	function (columns) {
	    global_columns = columns;
	    global_timer = setTimeout(update_dataset,100);
	    update_plot()
	}
    );
}

function on_dataset_update(time) {
    time = 1E3*time;
    if (time > global_time) {
	global_time = time;
	_update_dataset();
    }
    else {
	global_timer = setTimeout(update_dataset,1000);
    }
}

function update_dataset() {
    send_command(
	'dataset-status',
	{path:global_path},
	on_dataset_update
    )
}

function on_load() {
    var root = document.getElementById(ROOTID);
    add_leaves(root,[]);
}

function on_resize() {
    update_plot();
}
window.onload = on_load;
window.onresize = on_resize;

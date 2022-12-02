var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

var ROOT = '_data';
var ROOTID = 'root';
var ROOTTOKEN = '_tree';

var XID = 'x-axis';
var YID = 'y-axis';

var PLOTID = 'plot';
var MDID = 'metadata';
var UPDATING = 'updating';

var json_viewer = new JSONViewer();

var monitored_folders = new Set();

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

function data_hook(s) {
    return s.replace(/\bNaN\b/g, "null");
}

function format_path_list(path) {
    return [ROOTTOKEN].concat(path).join('/');
}

function parse_path_string(path_string) {
    return path_string.split('/').slice(1);
}

function add_leaves(parent,folder) {    
    send_command(
	'get-dir',
	{folder:folder},
	add_leaves_cb(parent,folder)
    );
}

function add_folder(parent,root_folder,folder,recent) {
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
    bu.classList.toggle('recent',recent);
    
    li.setAttribute('id',format_path_list(new_folder));
    
    cb.setAttribute('type','checkbox');
    cb.setAttribute('tabindex',-1);
    cb.onchange = function () {	
	var li = this.parentElement.parentElement;
	li.querySelector(':scope > sp > button').classList.remove('recent');
	var ul = li.querySelector('ul');
	var fmtpath = li.getAttribute('id')
	var path = parse_path_string(fmtpath);
	if (cb.checked) {
	    var pul = li.parentElement;
	    pul.insertBefore(li,pul.children[0]);
	    add_leaves(ul,path);
	    monitored_folders.add(fmtpath);
	}
	else {
	    ul.querySelectorAll('li').forEach(
		el => monitored_folders.delete(el.id)
	    )
	    while (ul.lastElementChild) {
		ul.removeChild(ul.lastElementChild);
	    }
	    monitored_folders.delete(fmtpath);
	}
    }
    bu.onclick = function () {cb.click();};	
}

function add_dataset(parent,root_folder,dataset,recent) {
    var li = document.createElement('li');
    var bu = document.createElement('button');

    parent.appendChild(li);
    li.appendChild(bu);

    li.setAttribute('id',format_path_list(root_folder.concat(dataset)));
    bu.innerText = dataset;
    bu.classList.add('dataset');
    bu.classList.toggle('recent',recent);
    bu.onclick = function () {
	bu.classList.remove('recent');
	var path = parse_path_string(bu.parentElement.getAttribute('id'));
	set_dataset(path);
    };
}

function add_leaves_cb(parent,root_folder) {
    return function (data) {
	var datasets = data[0];
	var folders = data[1]; 
	folders.forEach(
	    function (folder) {
		add_folder(parent,root_folder,folder,false);
	    }
	);
	datasets.forEach(
	    function (dataset) {
		add_dataset(parent,root_folder,dataset,false);
	    }
	);
    }
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
    global_time = null;
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
    send_command(
	'get-metadata',
	{path:format_md_path(path)},
	function (metadata) {
	    json_viewer.showJSON(metadata,-1,-1);
	}
    )
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
		},
		data_hook
    );
}

function format_md_path(ds_path) {
    var md_path = ds_path.slice();
    var ds_name = md_path.pop();
    var md_name_segments = ds_name.split('.');
    md_name_segments.pop();
    md_name_segments.push('bmd')
    var md_name = md_name_segments.join('.');
    md_path.push(md_name);
    return md_path;
}

function on_dataset_update(time) {
    if (global_time == null) {
	global_time = time;
    }
    if (
	(
	    time > global_time
	) && (
	    document.getElementById(UPDATING).checked
	)
    ){
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

function updating() {
    return 
}

function on_load() {
    var root = document.getElementById(ROOTID);
    add_leaves(root,[]);
    document.getElementById(MDID).appendChild(json_viewer.getContainer());
    update_folders();
}

function update_folders() {
    monitored_folders.forEach(
	function (fmtpath) {
	    send_command(
		'get-dir',
		{folder:parse_path_string(fmtpath)},
		function (folderl) {
		    if (monitored_folders.has(fmtpath)) {
			var datasets = folderl[0];
			var folders = folderl[1];
			var li = document.getElementById(fmtpath);
			var ul = li.querySelector('ul');
			var current_children = {};
			ul.querySelectorAll(':scope > li').forEach(
			    function(el) {
				current_children[parse_path_string(el.id).pop()] = el; 
			    }
			)
			var path = parse_path_string(fmtpath);
			folders.forEach(
			    function (folder) {
				if (
				    !(
					folder in current_children
				    )
				) {
				    add_folder(ul,path,folder,true);
				}				
			    }
			);
			datasets.forEach(
			    function (dataset) {
				if (
				    !(
					dataset in current_children
				    )
				){
				    add_dataset(ul,path,dataset,true);
				}
			    }
			)
			for (const name in current_children) {
			    if (
				datasets.indexOf(name) < 0
				    &&
				    folders.indexOf(name) < 0
			    ) {
				el = current_children[name];
				monitored_folders.delete(el.id);
				el.querySelectorAll('li').forEach(
				    el => monitored_folders.delete(el.id)
				)
				ul.removeChild(el);
			    }
			}
		    }
		}
	    )
	}
    )
    setTimeout(update_folders,4000);
}

function on_resize() {
    update_plot();    
}
window.onload = on_load;
window.onresize = on_resize;

// beckhttp protocol constants
var JSON_TYPE = 'application/json';
var COMMAND = 'command';
var PARAMETERS = 'parameters';

var data = [];

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

var layout = {
    yaxis: {title: 'pressure (mbar)'},
    title: 'pressure monitor'
}
var hscale = 0.95;
var vscale = 0.75;
function update_plot () {
    var xdata = data.map((pair) => pair[0]);    
    var ydata = data.map((pair) => pair[1]);
    layout['width'] = hscale * window.innerWidth;
    layout['height'] = vscale * window.innerHeight;
    var plotdata = [
        {
            x:xdata, y:ydata, mode: 'markers', type: 'scatter'
        }
    ];
    Plotly.newPlot(
        'plot',plotdata,layout
    );
}

function loop() {
    send_command(
        'get-input',
        {},
        function (value) {
            var dt = new Date();
            var y = value
            data.push([dt,y])            
            while (
                !document.getElementById('infinite').checked
                &&
                dt - data[0][0]
                > 
                document.getElementById('sample-history').value * 1e3
            ) {
                data.shift();
            }
            update_plot();
            setTimeout(
                loop,
                document.getElementById('sample-interval').value*1e3
            )
        }
    )
}

function on_load() {
    document.getElementById('clear').onclick = function () {data = [];}
    loop();
}
window.onload = on_load;
window.onresize = update_plot;
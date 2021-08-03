var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

var delay = 100; // milliseconds

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

var wl_div;

function on_wavelength (wavelength) {
    wl_div.innerText = wavelength;
    setTimeout(on_timeout,delay);
}
function on_timeout() {
    send_command(
	'get wavelength',
	{},
	on_wavelength
    )
}
function on_load() {
    wl_div = document.getElementById('wavelength');
    setTimeout(on_timeout,delay);
}

window.onload = on_load;

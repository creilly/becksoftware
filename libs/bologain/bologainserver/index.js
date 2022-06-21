// beckhttp protocol constants
var JSON_TYPE = 'application/json';
var COMMAND = 'command';
var PARAMETERS = 'parameters';

var gain_cell;
var gains_select;
var set_gain_button;

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

var deltat = 5 * 1000;

function loop() {
	get_gain();
	setTimeout(loop,deltat);
}

function update_gain(gain) {
	gain_cell.innerHTML = gain;
}

function get_gain() {
	send_command('get-gain',{},update_gain);
}

function set_gain() {
	var gain = parseInt(gains.value);
	send_command('set-gain',{gain:gain},function (x) {get_gain();});
}

function on_load() {
    gains_select = document.getElementById('gains');

    set_gain_button = document.getElementById('set-gain');
    set_gain_button.onclick = set_gain;

	gain_cell = document.getElementById('gain');
    
    loop();
}
window.onload = on_load;
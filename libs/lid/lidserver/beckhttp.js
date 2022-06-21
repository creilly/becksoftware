// beckhttp protocol constants
var JSON_TYPE = 'application/json';
var COMMAND = 'command';
var PARAMETERS = 'parameters';

function _do_nothing(x) {}

function send_command(command, parameters={}, cb=_do_nothing, errcb=_do_nothing, hook = (x) => x) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {	
        if (this.readyState == 4) {
            var resp = JSON.parse(hook(xhttp.responseText));
            if (resp != null && resp._error != undefined) {
                errcb(resp._error);
            }
            else {
                cb(resp);
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
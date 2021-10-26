var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

var WSET = 'wnum-set';
var WACT = 'wnum-act';
var LOCKING = 'locking';
var SETWINPUT = 'set-wnum-input';
var SETWBUTTON = 'set-wnum-button';
var LOCK = 'lock';
var UNLOCK = 'unlock';

var update_interval = 500; // milliseconds

function send_command(command, parameters, cb = null) {
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {	
	if (this.readyState == 4 && cb != null) {
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

function on_get_wnum_set(wnum) {
    document.getElementById(WSET).innerHTML = wnum.toFixed(5);
}

function on_get_wnum_act(wnum) {
    document.getElementById(WACT).innerHTML = wnum.toFixed(5);
}

function on_get_locking(locking) {
    el = document.getElementById(LOCKING);
    el.innerHTML = locking ? 'locking' : 'not locking';
    el.classList.toggle('locking',locking);
}

function on_set_wnum() {
    set_wnum(parseFloat(document.getElementById(SETWINPUT).value));
}

function on_set_lock() {
    set_locking(true);
}

function on_set_unlock() {
    set_locking(false);
}

function get_wnum_set() {
    send_command('get-wavenumber-set',{},on_get_wnum_set)
}

function get_wnum_act() {
    send_command('get-wavenumber-act',{},on_get_wnum_act)
}

function get_locking() {
    send_command('get-locking',{},on_get_locking)
}

function set_wnum(wavenumber) {
    send_command('set-wavenumber',{wavenumber:wavenumber});
}

function set_locking(locking) {
    send_command('set-locking',{locking:locking});
}

function update_interface() {
    get_wnum_set() 
    get_wnum_act() 
    get_locking()
    setTimeout(update_interface,update_interval);
}

function on_load() {
    update_interface();
    document.getElementById(SETWBUTTON).onclick = on_set_wnum;
    document.getElementById(LOCK).onclick = on_set_lock;
    document.getElementById(UNLOCK).onclick = on_set_unlock;
}

window.onload = on_load;


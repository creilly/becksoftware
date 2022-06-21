var angle_cell;
var angle_input;
var angle_button;

var moving_cell;
var stop_button;

var min_cell;
var min_input;
var min_button;

var max_cell;
var max_input;
var max_button;

var status_date;
var status_time;
var status_command;
var status_result;
var status_details;
var status_poll;

var deltat = 1 * 1000;

var poll_count = 0;

function loop() {
	get_angle();
    get_moving();
    get_min();
    get_max();
    update_poll_count();
	setTimeout(loop,deltat);
}

function update_poll_count() {
    poll_count += 1;
    status_poll.innerHTML = poll_count;
}

function get_moving() {
    _get_param(
        'get-moving',
        moving_cell,
        moving => moving ? 'true' : 'false'
    );
}

function _get_update_param_cb(element,hook) {
    return function (value) {
        console.log(element,value);
        element.innerHTML = hook(value);
    }
}

function _get_param(command,element,hook) {
    send_command(command,{},_get_update_param_cb(element,hook));
}

function _get_angle(command,element) {    
    _get_param(command,element,angle => angle.toFixed(2));
}

function get_angle() {
	_get_angle('get-lid',angle_cell);
}

function get_min() {    
    _get_angle('get-phi-min',min_cell);
}

function get_max() {
    _get_angle('get-phi-max',max_cell);
}

function _send_command(command,params={}) {
    send_command(
        command,params,
        (x) => set_status(command,true),
        (x) => set_status(command,false,x)
    );
}

function _set_angle(command,key,input,getter) {
    var angle = parseFloat(input.value);
    console.log('angle',angle);
	_send_command(command,{[key]:angle});
    getter();
}

function set_angle() {
    _set_angle('set-lid','phi',angle_input,get_angle);
}

function set_min() {
    _set_angle('set-phi-min','phi_min',min_input,get_min);
}

function set_max() {
    _set_angle('set-phi-max','phi_max',max_input,get_max);
}

function set_status(command,result,details='') {
    var date = new Date();
    status_date.innerHTML = date.toLocaleDateString();
    status_time.innerHTML = date.toLocaleTimeString();
    status_command.innerHTML = command;
    status_result.innerHTML = result ? 'success' : 'error';
    status_details.innerHTML = details;
}

function stop_lid() {
    _send_command('stop-lid');
}

function on_load() {
    angle_cell = document.getElementById('angle');

    angle_button = document.getElementById('set-angle');
    angle_button.onclick = set_angle;

	angle_input = document.getElementById('angle-input');

    moving_cell = document.getElementById('moving');
    stop_button = document.getElementById('stop');
    stop_button.onclick = stop_lid;

    min_cell = document.getElementById('min');
    min_button = document.getElementById('set-min');
    min_button.onclick = set_min;
    min_input = document.getElementById('min-input');

    max_cell = document.getElementById('max');
    max_button = document.getElementById('set-max');
    max_button.onclick = set_max;
    max_input = document.getElementById('max-input');

    status_date = document.getElementById('status-date');
    status_time = document.getElementById('status-time');
    status_command = document.getElementById('status-command');
    status_result = document.getElementById('status-result');
    status_details = document.getElementById('status-details');    
    status_poll = document.getElementById('status-poll');    
    
    loop();
}
window.onload = on_load;
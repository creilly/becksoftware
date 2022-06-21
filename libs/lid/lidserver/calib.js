var calib_input;
var calib_button;
var result_cell;
var details_cell;

function handle_set(resp,error) {
    console.log('resp',resp);
    if (error) {
        result_cell.innerHTML = 'error';
        details_cell.innerHTML = resp;
    }
    else {
        result_cell.innerHTML = 'success';
        details_cell.innerHTML = '';
    }
}

function set_calib() {
	var angle = parseFloat(calib_input.value);
	send_command(
        'calibrate-lid',
        {phi_o:angle},
        (x) => handle_set(x,false),
        (x) => handle_set(x,true)
    );
}

function on_load() {
    calib_button = document.getElementById('set-calib');
    calib_input = document.getElementById('calib-input');
    result_cell = document.getElementById('result');
    details_cell = document.getElementById('details');    
    calib_button.onclick = set_calib;	
}
window.onload = on_load;
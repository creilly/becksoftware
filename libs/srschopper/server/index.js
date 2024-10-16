var canvas;
var cw;
var ch;
var cb = 0.025;

var delays = [];
var controls = [];
var times = [];

var deltat = 60; // seconds
var dmin = 0.000; // seconds
var dmax = 0.025;
var cmin = 0.0; // volts
var cmax = 5.0;

var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

function send_command(command, parameters, cb = null) {
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {	
        if (this.readyState == 4) {       
            var response = JSON.parse(xhttp.responseText);
            if (
                typeof yourVariable === 'object' &&
                !Array.isArray(yourVariable) &&
                yourVariable !== null &&
                '_error' in response
            ) {
                console.log('error!',response['_error'])
            }
            else{
                if (cb !== null) {
                    cb(response)
                };
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

function update_plot(delay,control) {
    delays.push(delay);
    controls.push(control);
    var time = Date.now() / 1e3;
    times.push(time);
    while (time - times[0] > deltat) {
        times.shift();
        delays.shift();
        controls.shift();
    }
    var tmax = time;
    var tmin = tmax - deltat;
    var xs = times.map((t) => (cb + (1-2*cb) * (t - tmin) / (tmax-tmin)) * canvas.width);
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,cw,ch);   
    ctx.strokeStyle = 'black';
    ctx.beginPath();
    ctx.moveTo(cb*cw,cb*ch);
    ctx.lineTo(cb*cw,(1-cb)*ch);
    ctx.lineTo((1-cb)*cw,(1-cb)*ch);
    ctx.lineTo((1-cb)*cw,cb*ch);
    ctx.lineTo(cb*cw,cb*ch);
    ctx.stroke();
    for (var i = 0; i < 2; i++) {
        var zs = i ? delays : controls;
        var zmin = i ? dmin : cmin;
        var zmax = i ? dmax : cmax;
        var color = i ? 'red' : 'blue';
        var ys = zs.map((z) => (cb + (1-2*cb) * (zmax - z) / (zmax-zmin)) * canvas.height);        
        ctx.strokeStyle = color;
        ctx.beginPath();        
        ctx.moveTo(xs[0],ys[0]);
        for (var j = 0; j < ys.length; j++) {
            ctx.lineTo(xs[j],ys[j]);
        }
        ctx.stroke();
    }
}
function on_control(delay) {
    function _on_control(control) {
        document.getElementById('control-value').innerHTML = control.toFixed(3);
        update_plot(delay,control);
        setTimeout(loop,50);
    }
    return _on_control
}
function on_delay(delay) {
    send_command(
        'get control',{},on_control(delay)
    );
}
function loop() {
    send_command(
        'get delay',{},on_delay
    )
}
function control_cb() {    
    if (document.getElementById('control-active').checked){        
        send_command(
            'set control',            
            {control:parseFloat(document.getElementById('control-input').value)}
        );
    }
}

function locking_cb() {
    send_command(
        'set locking',
        {locking:document.getElementById('locking-input').checked}
    )
}

function setpoint_cb() {
    if (document.getElementById('setpoint-active').checked){
        send_command(
            'set setpoint',            
            {setpoint:1e-3*parseFloat(document.getElementById('setpoint-input').value)}
        );
    }
}

var CONTROL = 0;
var LOCKING = 1;
var SETPOINT = 2;
var properties = [LOCKING,SETPOINT];
var property_index = 0;
function property_loop() {
    var property = properties[property_index];
    switch (property) {
        case LOCKING:
            send_command(
                'get locking',{},
                function (locking) {
                    document.getElementById('locking-value').innerHTML = locking;
                }
            )
            break;
        case SETPOINT:
            send_command(
                'get setpoint',{},
                function (setpoint) {
                    document.getElementById('setpoint-value').innerHTML = (1e3*setpoint).toFixed(2);
                }
            )
            break;
    }
    property_index += 1;
    if (property_index == properties.length) {
        property_index = 0;
    }
    setTimeout(property_loop,100)
}

function on_load() {
    canvas = document.getElementById('canvas');
    cw = canvas.width;
    ch = canvas.height;
    document.getElementById('control-input').oninput = control_cb;
    document.getElementById('locking-submit').onclick = locking_cb;
    document.getElementById('setpoint-input').oninput = setpoint_cb;
    property_loop();
    loop();
}

window.onload = on_load;
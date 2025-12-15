var context;
var toggle = true;
var pindex = true;

var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

var audio;

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

function on_alert_update(alert) {     
    var sw = 3;
    context.beginPath();
    context.strokeStyle = 'black';
    context.lineWidth = sw;
    context.fillStyle = alert == null ? (
        toggle ? 'White' : 'MintCream'
    ) : (
        toggle ? 'Crimson' : 'CornflowerBlue'
    );
    context.arc(canvas.width/2,canvas.height/2,canvas.width/2 - sw,0,2*Math.PI);
    context.fill();
    context.stroke();    
    toggle = !toggle;
    document.getElementById('data').innerHTML = alert;        
    if (alert == null) {
        if (!audio.paused) {        
            audio.pause();        
        }         
    }
    else {        
        if (audio.paused) {
            if (!audio.muted) {
                audio.play();
            }            
        }        
    }
}

function loop() {    
    send_command('get alert',{},on_alert_update);
    setTimeout(loop,250);
}

function on_toggle() {
    audio.muted = !audio.muted;
    if (audio.paused) {
        audio.play();
    }
    document.getElementById('sound').innerHTML = audio.muted ? 'muted' : 'on';
}

function on_load() {
    canvas = document.getElementById('alert');
    context = canvas.getContext('2d');    
    audio = new Audio('alarm.m4a');
    audio.muted = true;
    audio.loop = true;            
    document.getElementById('toggle').onclick = on_toggle;    
    document.getElementById('clear').onclick = function () {        
        send_command('clear alert',{});
    }    
    loop();    
}

window.onload = on_load;
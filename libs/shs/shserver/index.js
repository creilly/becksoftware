var JSON_TYPE = 'application/json';

var COMMAND = 'command';
var PARAMETERS = 'parameters';

var heartbeat = 0;

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

function get_prop_cb(command,fmt) {    
    return val => {
        // console.log(command,fmt,val,fmt(val));
        document.getElementById(command).innerHTML = fmt(val); 
    }
}

var dummy = x => x;
var param_props = [
    ['cc','get cc',3,0],
    ['cc-sp','get cc sp',3,0],
    ['cv','get cv',3,0],
    ['ev','get ev',1,0],
    ['ev-sp','get ev sp',1,0],
    ['ec','get ec',2,3]
].map(
    param => [
        param[1], param[0], val => (parseFloat(val) * 10**param[3]).toFixed(param[2])
    ]
);    
var props = [
    ['get temperature','temperature',dummy], 
    ['get operation mode','operation-mode',mode => ({0:'standby',1:'operate'})[mode]],
    ['get heating mode','heating-mode',mode => ({0:'resistive',1:'ebeam'})[mode]],
    ['get remote mode','remote-mode',mode => ({0:'touch-panel',1:'remote'})[mode]],
    ['get hv','hv',enabled => enabled ? 'on' : 'off']
].concat(param_props)
var prop_index = 0;
function property_loop() {
    var prop = props[prop_index]    
    send_command(prop[0], {}, get_prop_cb(prop[1],prop[2]));
    prop_index += 1
    if (prop_index == props.length) {
        prop_index = 0;
        heartbeat++;
        document.getElementById('heartbeat').innerHTML = heartbeat;
    }
    setTimeout(property_loop,50);    
}

function get_op_mode_cb(opmode) {
    return () => {
        send_command(opmode,{});
    };
}

function get_paramset_cb(command, param, input) {    
    return () => send_command(
        command, {
            [param]:parseFloat(
                document.getElementById(input).value
            )
        }
    );
}

function get_heating_mode_cb(heating_mode) {
    return () => send_command(
        'set heating mode', {'heating_mode':heating_mode}
    );
}

function on_load() {    
    document.getElementById('release-control').onclick = () => {
        send_command('release control', {})
    };
    for (
        var opmode of [
            ['standby','goto standby'],
            ['operate','goto operate']
        ]
    ) {
        document.getElementById(opmode[0]).onclick = get_op_mode_cb(opmode[1]);
    }
    for (
        var paramset of [
            ['cc-sp-button','cc-sp-input','set cc sp','cc'],
            ['ev-sp-button','ev-sp-input','set ev sp','ev']
        ]
    ) {
        document.getElementById(paramset[0]).onclick = get_paramset_cb(
            paramset[2], paramset[3], paramset[1]
        )
    }
    for (
        var hm of [
            ['res-button',0],['eb-button',1]
        ]
    ) {
        document.getElementById(hm[0]).onclick = get_heating_mode_cb(hm[1]);
    }
    document.getElementById('hv-button').onclick = function () {
        send_command(
            'set hv', {
                enabled:{
                    0:false, 1:true
                }[document.querySelector('input[name="hv"]:checked').value]
            }
        )
    };
    property_loop();    
}

window.onload = on_load;
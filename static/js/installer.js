document.addEventListener("DOMContentLoaded", createForm);

function createForm() {
    let nodeNumber = window.nodeNumber;
    
    if (typeof nodeNumber == 'undefined')
        nodeNumber = 0;
    
    let initForm = document.forms[0];
    let lastForm = document.forms[document.forms.length - 1];
    
    let newForm = initForm.cloneNode(true);
    if (initForm.style.display != 'none') {
        initForm.style.display = 'none'
    }
    newForm.style.display = 'block';
    
    lastForm.after(newForm);
    nodeNumber++;
    newForm.id = 'form' + nodeNumber;
    
    let nameDiv = newForm.querySelector('.nodeName')
    let nodeName = 'Node' + "00".slice(nodeNumber.toString().length) + nodeNumber
    nameDiv.innerHTML = "<b>" + nodeName + "</b>"
    
    let seedNodeSelector = document.querySelector('.seedNode').querySelector('select')
    let newOption = document.createElement('option');
    newOption.value = 'form' + nodeNumber.toString();
    newOption.text = nodeName
    if (nodeNumber == 1)
        newOption.selected = 'selected';
    seedNodeSelector.add(newOption);
    
    window.nodeNumber = nodeNumber
    
    return newForm;
}

function addNode() {
    let newForm = createForm();

    let removeButton = document.createElement('button');
    removeButton.innerText = 'X';
    removeButton.name = 'removeNode'
    removeButton.addEventListener('click', removeNode);
    
    let newNodeHeader = newForm.querySelector('.nodeHeader')
    newNodeHeader.appendChild(removeButton);
}

function removeNode(e) {
    let formToDelete = event.target.closest('form');
    let contentContainer = document.querySelector('#content')
    let seedNodeSelector = document.querySelector('.seedNode').querySelector('select')
    let selectorOptions = seedNodeSelector.getElementsByTagName('option')
    for (let option of selectorOptions) {
        if (option.value == formToDelete.id)
            seedNodeSelector.removeChild(option);       
    }
    contentContainer.removeChild(formToDelete);
}

function regularInput(e) {
    event.target.classList.remove("emptyInput");
}

function submitForm() {
    if (isInputValid()) {
        sendFormData() 
    }
}

function isInputValid() {
    let forms = document.forms
    let isInvalid = false;
    let clusterNameInput = document.querySelector("input[name='cluster_name']")
    for (let i = 1; i < forms.length; i++) {
        inputList = forms[i].querySelectorAll("input[type='text']")
        for (var input of inputList) {
            if (input.value == '' || input.name == 'port' && input.value.match(/\D/) != null) {
                input.classList.add("emptyInput");
                isInvalid = true;
            }
        }
    }
    if (clusterNameInput.value == '') {
        clusterNameInput.classList.add("emptyInput");
        isInvalid = true;
    }
    if (isInvalid) {
        return false
    }
    return true
}

async function sendFormData() {
    let seedNodeSelector = document.querySelector('.seedNode').querySelector('select')
    let seedNodeForm = document.getElementById(seedNodeSelector.selectedOptions[0].value)    
    let clusterName = document.querySelector("input[name='cluster_name']").value
    let arrayOfForms = []
    let objectToJSON = {}
    
    let seedNodeFormData = new FormData(seedNodeForm)
    let seedNodeHost = seedNodeFormData.get('host')
    
    let forms = document.forms
    for (let i = 1; i < forms.length; i++) {
        let formData = new FormData(forms[i])
        
        formData.append('cluster_name', clusterName);
        formData.append('seed_node', seedNodeHost);
        
        let formDataObj = {};
        for (let [name, value] of formData) {
            if (value == '')
                value = 'null'
            formDataObj[name] = value;
        }
        arrayOfForms.push(formDataObj)
    }
    objectToJSON['nodes'] = arrayOfForms
    let response = await fetch('/install', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json; charset=utf-8'
        },
        body: JSON.stringify(objectToJSON)
    });
    openModalWindow()
}

function forceInstallStatusChange(e) {
    checkBox = event.target
    if (checkBox.checked) {
        if (! window.confirm('Warning!\rThis option will force your ScyllaDB installation (even if another installation is already running on this host)!\rDo you really want to continue?')) {
            checkBox.checked = false
        }
    }
}

async function openModalWindow() {
    modalWindowBackground.style.display = "block";
    window.controller = new AbortController();
    messageString = document.querySelector('#statusMessage');
    let objectToJSON = {"host": ''}
    let response;
    try {
        response = await fetch('/status', {
            signal: window.controller.signal,
            method: 'POST',
            headers: {
            'Content-Type': 'application/json; charset=utf-8'
        },
        body: JSON.stringify(objectToJSON)
        });
    }
    catch(err) {
        return
    }
    if (response.ok) {
        let json = await response.json();
        if (json['message'] == '') {
            messageString.innerText = 'No active installations found';
        }
        else {
            messageString.innerText = ''
            for (let item of json['message']) {
                getProgress(host=item['host'])
            }
        }
    }
    else {
        alert("HTTP Error: " + response.status);
    }
}

async function getProgress(host) {
    let succeededIcon = '<img src="../../static/img/succeeded.png" alt="Succeeded">'
    let inProgressIcon = '<img src="../../static/img/in_progress.png" alt="In Progress">'
    let failedIcon = '<img src="../../static/img/failed.png" alt="Failed">'
    
    let tableHead = document.querySelector('thead');
    let tableHeadRow = tableHead.querySelector('tr');
    let tableHeadColumns = tableHeadRow.querySelectorAll('th');
    let tableBody = document.querySelector('tbody');
    let newRow = document.createElement('tr');
    tableBody.appendChild(newRow);
    for (let i = 1; i <= tableHeadColumns.length; i++){
        newCell = document.createElement('td');
        newRow.appendChild(newCell)
    }
    newRow.firstChild.innerText = host
    newRow.lastChild.innerHTML = inProgressIcon
    
    let objectToJSON = {"host": host}
    let response;
    let globalStatus;
    let inProgress = true
    while (inProgress) {
        try {
            response = await fetch('/status', {
                signal: window.controller.signal,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=utf-8'
                },
                body: JSON.stringify(objectToJSON)
            });
        }
        catch(err) {
            return
        }
        if (response.ok) {
            let json = await response.json();
            for (let record of json['message']) {
                switch(record['status_name'].toUpperCase()){
                    case 'OS IDENTIFIED':
                        newRow.querySelectorAll('td')[1].innerHTML = succeededIcon;
                        break;
                    case 'SCYLLA INSTALLED':
                        newRow.querySelectorAll('td')[2].innerHTML = succeededIcon;
                        break;
                    case 'SCYLLA.YAML CREATED':
                        newRow.querySelectorAll('td')[3].innerHTML = succeededIcon;
                        break;
                    case 'SCYLLA CONFIGURED':
                        newRow.querySelectorAll('td')[4].innerHTML = succeededIcon;
                        break;
                    case 'SCYLLA STARTED':
                        newRow.querySelectorAll('td')[5].innerHTML = succeededIcon;
                        break;
                    case 'CASSANDRA-STRESS COMPLETED' :
                        newRow.querySelectorAll('td')[6].innerHTML = succeededIcon;
                        break;
                }
            }
            if (json['message'] != '') {
                globalStatus = json['message'][0]['global_status']
                if (globalStatus.toUpperCase() != 'IN PROGRESS') {
                    inProgress = false
                }
            }
        }   
    }
    newRow.lastChild.innerHTML = (globalStatus.toUpperCase() == 'SUCCEEDED') ? succeededIcon : failedIcon;
}

function closeModalWindow() {
    window.controller.abort();
    modalWindowBackground.style.display = "none";
    messageString = document.querySelector('#statusMessage');
    messageString.innerText = 'Looking for active installations...'
    let tableBody = document.querySelector('tbody');
    while (tableBody.firstChild) {
        tableBody.removeChild(tableBody.firstChild);
    }
}
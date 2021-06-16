function createForm() {
    let nodeNumber = window.nodeNumber;
    
    if (typeof nodeNumber == 'undefined')
        nodeNumber = 0;
    
    let initForm = document.forms[0];
    let lastForm = document.forms[document.forms.length - 1];
    
    let newForm = initForm.cloneNode(true);
    newForm.style.display = 'block';
    
    lastForm.after(newForm);
    nodeNumber++;
    newForm.id = 'form' + nodeNumber;
    
    let nameDiv = newForm.querySelector('.node_name')
    let nodeName = 'Node' + "00".slice(nodeNumber.toString().length) + nodeNumber
    nameDiv.innerHTML = "<b>" + nodeName + "</b>"
    
    let seedNodeSelector = document.querySelector('.seed_node').querySelector('select')
    let newOption = document.createElement('option');
    newOption.value = 'form' + nodeNumber.toString();
    newOption.text = nodeName
    if (nodeNumber == 1)
        newOption.selected = 'selected';
    seedNodeSelector.add(newOption);
    
    window.nodeNumber = nodeNumber
    
    return newForm;
}

document.addEventListener("DOMContentLoaded", createForm);

function addNode() {
    let newForm = createForm();
    
    let removeDiv = document.createElement('div')
    removeDiv.className = 'remove'
    
    let removeButton = document.createElement('input');
    removeButton.type = 'button';
    removeButton.value = 'Remove node';
    removeButton.addEventListener('click', removeNode);
    
    let newNodeContainer = newForm.querySelector('.node_container')
    newNodeContainer.appendChild(removeDiv);
    removeDiv.appendChild(removeButton);
}

function removeNode(e) {
    let formToDelete = event.target.closest('form');
    
    let seedNodeSelector = document.querySelector('.seed_node').querySelector('select')
    let selectorOptions = seedNodeSelector.getElementsByTagName('option')
    for (let option of selectorOptions) {
        if (option.value == formToDelete.id)
            seedNodeSelector.removeChild(option);       
    }
    
    document.body.removeChild(formToDelete);
}
async function sendFormData() {
    let seedNodeSelector = document.querySelector('.seed_node').querySelector('select')
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
        for(let [name, value] of formData) {
            if (value == '')
                value = 'null'
            formDataObj[name] = value;
        }
        console.log(formDataObj)
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
}      
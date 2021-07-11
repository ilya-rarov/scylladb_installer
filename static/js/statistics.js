document.addEventListener("DOMContentLoaded", getStatistics);

async function getStatistics() {
    let tableBody = document.querySelector('tbody');
    while (tableBody.firstChild) {
        tableBody.removeChild(tableBody.firstChild);
    }
    messageString = document.querySelector('#statusMessage');
    messageString.innerText = 'Looking for completed installations...'
    
    let formData = new FormData(document.querySelector("form[name='filter']"))
    
    let formDataObj = {}
    
    for (let [name, value] of formData) {
        formDataObj[name] = value;
    }
    
    response = await fetch('/get_stat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json; charset=utf-8'
        },
        body: JSON.stringify(formDataObj)
    });
    if (response.ok) {
        let json = await response.json();
        if (json['message'] == '') {
            messageString.innerText = 'No completed installations found';
        }
        else {
            messageString.innerText = ''
            generatStatTable(statArray=json['message'])
        }
    }
    else {
        alert("HTTP Error: " + response.status);
    }    

}

function generatStatTable(statArray) {
    let tableHead = document.querySelector('thead');
    let tableHeadRow = tableHead.querySelector('tr');
    let tableHeadColumns = tableHeadRow.querySelectorAll('th');
    let tableBody = document.querySelector('tbody');
    for (let item of statArray) {
        let newRow = document.createElement('tr');
        tableBody.appendChild(newRow);
        for (let i = 0; i < tableHeadColumns.length; i++){
            newCell = document.createElement('td');
            newCell.innerText = item[i]
            newRow.appendChild(newCell)
        }
    }
}
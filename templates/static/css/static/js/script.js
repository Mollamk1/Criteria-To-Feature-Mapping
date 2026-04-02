const jsonInput = document.getElementById('jsonInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const resultsSection = document.getElementById('resultsSection');
const resultsContainer = document.getElementById('resultsContainer');
const printBtn = document.getElementById('printBtn');
const downloadBtn = document.getElementById('downloadBtn');
const watThreshold = document.getElementById('watThreshold');

// Analyze button
analyzeBtn.addEventListener('click', async () => {
    const jsonText = jsonInput.value.trim();
    
    if (!jsonText) {
        showError('Please paste JSON data in the text area');
        return;
    }

    let data;
    try {
        data = JSON.parse(jsonText);
    } catch (e) {
        showError(`Invalid JSON: ${e.message}`);
        return;
    }

    showLoading(true);
    errorMessage.classList.add('hidden');

    try {
        const formData = new FormData();
        // Create a blob from the JSON data
        const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
        formData.append('file', blob, 'data.json');
        formData.append('wat_threshold', watThreshold.value);

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const responseData = await response.json();

        if (!response.ok) {
            showError(responseData.error || 'An error occurred');
            showLoading(false);
            return;
        }

        displayResults(responseData.results);
        resultsSection.classList.remove('hidden');
        showLoading(false);
        
        // Scroll to results
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    } catch (error) {
        showError(`Error: ${error.message}`);
        showLoading(false);
    }
});

// Clear button
clearBtn.addEventListener('click', () => {
    jsonInput.value = '';
    resultsSection.classList.add('hidden');
    errorMessage.classList.add('hidden');
    jsonInput.focus();
});

function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
}

function showLoading(show) {
    if (show) {
        loadingIndicator.classList.remove('hidden');
    } else {
        loadingIndicator.classList.add('hidden');
    }
}

function displayResults(results) {
    resultsContainer.innerHTML = '';

    for (const [category, criteria] of Object.entries(results)) {
        const tableTitle = document.createElement('div');
        tableTitle.className = 'table-title';
        tableTitle.textContent = category;
        resultsContainer.appendChild(tableTitle);

        const table = document.createElement('table');
        table.className = 'results-table';

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        ['Criteria Name', 'Features Mapped', 'Feature Results', 'Formula', 'Result'].forEach(header => {
            const th = document.createElement('th');
            th.textContent = header;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        criteria.forEach(criterion => {
            const row = document.createElement('tr');
            
            const nameCell = document.createElement('td');
            nameCell.textContent = criterion.criteria_name;
            nameCell.style.fontWeight = '600';
            row.appendChild(nameCell);
            
            const featuresCell = document.createElement('td');
            featuresCell.textContent = criterion.features_mapped;
            featuresCell.style.fontSize = '0.85em';
            row.appendChild(featuresCell);
            
            const resultCell = document.createElement('td');
            resultCell.textContent = criterion.feature_results;
            resultCell.style.fontSize = '0.85em';
            row.appendChild(resultCell);
            
            const formulaCell = document.createElement('td');
            formulaCell.textContent = criterion.formula;
            formulaCell.style.fontSize = '0.8em';
            formulaCell.style.color = '#666';
            row.appendChild(formulaCell);
            
            const resultValueCell = document.createElement('td');
            const result = criterion.result;
            const badge = document.createElement('span');
            badge.className = 'result-badge';
            
            if (result === 'True' || result === 'true') {
                badge.classList.add('true');
                badge.textContent = 'True';
            } else if (result === 'False' || result === 'false') {
                badge.classList.add('false');
                badge.textContent = 'False';
            } else {
                badge.classList.add('value');
                badge.textContent = result;
            }
            
            resultValueCell.appendChild(badge);
            row.appendChild(resultValueCell);
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        resultsContainer.appendChild(table);
    }
}

// Print button
printBtn.addEventListener('click', () => {
    window.print();
});

// Download button
downloadBtn.addEventListener('click', () => {
    const resultsText = resultsContainer.innerText;
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(resultsText));
    element.setAttribute('download', 'criteria-results.txt');
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
});

// Auto-focus textarea on page load
document.addEventListener('DOMContentLoaded', () => {
    jsonInput.focus();
});

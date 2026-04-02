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

        console.log('[DEBUG] Sending request to /upload...');
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        console.log('[DEBUG] Response received:', response.status, response.statusText);
        let responseData;
        
        try {
            responseData = await response.json();
            console.log('[DEBUG] Response parsed:', responseData);
        } catch (parseError) {
            console.error('[ERROR] Failed to parse response as JSON:', parseError);
            showError(`Response parsing error: ${parseError.message}`);
            showLoading(false);
            return;
        }

        if (!response.ok) {
            console.error('[ERROR] Server returned error:', responseData);
            showError(responseData.error || `Server error (${response.status}): ${response.statusText}`);
            showLoading(false);
            return;
        }

        console.log('[DEBUG] Displaying results...');
        try {
            displayResults(responseData.results);
        } catch (displayError) {
            console.error('[ERROR] Failed to display results:', displayError);
            showError(`Failed to display results: ${displayError.message}`);
            showLoading(false);
            return;
        }

        resultsSection.classList.remove('hidden');
        showLoading(false);
        
        // Scroll to results
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    } catch (error) {
        console.error('[ERROR] Unexpected error:', error);
        showError(`Unexpected error: ${error.message}`);
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
    try {
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
            if (!criteria || !Array.isArray(criteria)) {
                console.error('[ERROR] Invalid criteria format:', category, criteria);
                continue;
            }

            criteria.forEach((criterion, index) => {
                try {
                    const row = document.createElement('tr');
                    
                    const nameCell = document.createElement('td');
                    nameCell.textContent = criterion.criteria_name || 'N/A';
                    nameCell.style.fontWeight = '600';
                    row.appendChild(nameCell);
                    
                    const featuresCell = document.createElement('td');
                    featuresCell.textContent = criterion.features_mapped || 'N/A';
                    featuresCell.style.fontSize = '0.85em';
                    row.appendChild(featuresCell);
                    
                    const resultCell = document.createElement('td');
                    resultCell.textContent = criterion.feature_results || 'N/A';
                    resultCell.style.fontSize = '0.85em';
                    row.appendChild(resultCell);
                    
                    const formulaCell = document.createElement('td');
                    formulaCell.textContent = criterion.formula || 'N/A';
                    formulaCell.style.fontSize = '0.8em';
                    formulaCell.style.color = '#666';
                    row.appendChild(formulaCell);
                    
                    const resultValueCell = document.createElement('td');
                    const result = criterion.result;
                    const badge = document.createElement('span');
                    badge.className = 'result-badge';
                    
                    if (result === 'True' || result === 'true') {
                        badge.classList.add('true');
                        badge.textContent = '✓ True';
                    } else if (result === 'False' || result === 'false') {
                        badge.classList.add('false');
                        badge.textContent = '✗ False';
                    } else {
                        badge.classList.add('value');
                        badge.textContent = result;
                    }
                    
                    resultValueCell.appendChild(badge);
                    row.appendChild(resultValueCell);
                    tbody.appendChild(row);
                } catch (rowError) {
                    console.error('[ERROR] Failed to create row', index, ':', rowError, criterion);
                }
            });
            table.appendChild(tbody);
            resultsContainer.appendChild(table);
        }
    } catch (displayError) {
        console.error('[ERROR] displayResults failed:', displayError);
        throw displayError;
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

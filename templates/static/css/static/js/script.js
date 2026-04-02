const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');
const resultsContainer = document.getElementById('resultsContainer');
const watThreshold = document.getElementById('watThreshold');

uploadArea.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        analyzeBtn.disabled = false;
    }
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    fileInput.files = e.dataTransfer.files;
    analyzeBtn.disabled = false;
});

analyzeBtn.addEventListener('click', async () => {
    if (!fileInput.files.length) {
        showError('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('wat_threshold', watThreshold.value);

    showLoading(true);
    errorMessage.classList.add('hidden');

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            showError(data.error || 'An error occurred');
            showLoading(false);
            return;
        }

        displayResults(data.results);
        resultsSection.classList.remove('hidden');
        showLoading(false);
    } catch (error) {
        showError(`Error: ${error.message}`);
        showLoading(false);
    }
});

function showError(message) {
    errorMessage.textContent = message;
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
            row.appendChild(nameCell);
            
            const featuresCell = document.createElement('td');
            featuresCell.textContent = criterion.features_mapped;
            row.appendChild(featuresCell);
            
            const resultCell = document.createElement('td');
            resultCell.textContent = criterion.feature_results;
            row.appendChild(resultCell);
            
            const formulaCell = document.createElement('td');
            formulaCell.textContent = criterion.formula;
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
        });
        table.appendChild(tbody);
        resultsContainer.appendChild(table);
    }
}

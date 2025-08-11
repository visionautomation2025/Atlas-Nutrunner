// Global Variables
let currentStep = 1;
let totalSteps = 9;
let cycleData = {
    barcode: '',
    finalTorque: 0,
    finalAngle: 0,
    result: '',
    cycleTime: 0,
    startTime: 0
};
let torqueChart;
let tighteningInterval;
let currentTorque = 0;
let currentAngle = 0;
let isPassSequence = true; // Toggle between pass/fail for demo
let dateTimeInterval; // For updating date and time
let cycleStarted = false; // Flag to track if cycle start button was clicked

// Barcode text management
function setBarcodeText(text) {
    const barcodeText = document.querySelector('.barcode-text');
    const barcodeLines = document.querySelector('.barcode-lines');
    
    if (barcodeText) {
        barcodeText.textContent = text;
        
        // Add blinking class for "Ready to scan..."
        if (text === 'Ready to scan...') {
            barcodeText.classList.add('blinking');
        } else {
            barcodeText.classList.remove('blinking');
        }
    }
    
    if (barcodeLines && text !== 'Ready to scan...') {
        // Generate visual 1D barcode
        generateBarcode(text, barcodeLines);
    } else if (barcodeLines) {
        // Clear barcode lines for "Ready to scan..."
        barcodeLines.innerHTML = '';
    }
}

// Generate visual 1D barcode
function generateBarcode(text, container) {
    container.innerHTML = '';
    
    // Simple 1D barcode generation
    // Each character gets converted to a pattern of bars
    const patterns = {
        'A': [1,0,1,1,0,0,0,0,1,0],
        'B': [1,0,1,1,0,0,0,1,0,0],
        'C': [1,0,1,1,0,0,1,0,0,0],
        'D': [1,0,1,1,0,0,1,1,0,0],
        'E': [1,0,1,1,0,1,0,0,0,0],
        'F': [1,0,1,1,0,1,0,1,0,0],
        'G': [1,0,1,1,0,1,1,0,0,0],
        'H': [1,0,1,1,0,1,1,1,0,0],
        'I': [1,0,1,1,1,0,0,0,0,0],
        'J': [1,0,1,1,1,0,0,1,0,0],
        'K': [1,0,1,1,1,0,1,0,0,0],
        'L': [1,0,1,1,1,0,1,1,0,0],
        'M': [1,0,1,1,1,1,0,0,0,0],
        'N': [1,0,1,1,1,1,0,1,0,0],
        'O': [1,0,1,1,1,1,1,0,0,0],
        'P': [1,0,1,1,1,1,1,1,0,0],
        'Q': [1,1,0,0,0,0,0,0,1,0],
        'R': [1,1,0,0,0,0,0,1,0,0],
        'S': [1,1,0,0,0,0,1,0,0,0],
        'T': [1,1,0,0,0,0,1,1,0,0],
        'U': [1,1,0,0,0,1,0,0,0,0],
        'V': [1,1,0,0,0,1,0,1,0,0],
        'W': [1,1,0,0,0,1,1,0,0,0],
        'X': [1,1,0,0,0,1,1,1,0,0],
        'Y': [1,1,0,0,1,0,0,0,0,0],
        'Z': [1,1,0,0,1,0,0,1,0,0],
        '0': [1,1,0,0,1,0,1,0,0,0],
        '1': [1,1,0,0,1,0,1,1,0,0],
        '2': [1,1,0,0,1,1,0,0,0,0],
        '3': [1,1,0,0,1,1,0,1,0,0],
        '4': [1,1,0,0,1,1,1,0,0,0],
        '5': [1,1,0,0,1,1,1,1,0,0],
        '6': [1,1,0,1,0,0,0,0,0,0],
        '7': [1,1,0,1,0,0,0,1,0,0],
        '8': [1,1,0,1,0,0,1,0,0,0],
        '9': [1,1,0,1,0,0,1,1,0,0]
    };
    
    // Add start pattern
    const startPattern = [1,0,1,0,1,0,1,0,1,0];
    let fullPattern = [...startPattern];
    
    // Convert each character to its pattern
    for (let char of text) {
        if (patterns[char]) {
            fullPattern = fullPattern.concat(patterns[char]);
        }
    }
    
    // Add stop pattern
    const stopPattern = [1,0,1,0,1,0,1,0,1,0];
    fullPattern = fullPattern.concat(stopPattern);
    
    // Create visual bars
    fullPattern.forEach((bar, index) => {
        const barElement = document.createElement('div');
        
        if (bar === 1) {
            // Black bar
            barElement.className = 'bar';
            barElement.style.width = '4px';
            barElement.style.height = '50px';
            barElement.style.backgroundColor = '#000';
            barElement.style.marginRight = '2px';
            barElement.style.display = 'inline-block';
            barElement.style.borderRadius = '1px';
            barElement.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.3)';
        } else {
            // White space
            barElement.className = 'space';
            barElement.style.width = '3px';
            barElement.style.height = '50px';
            barElement.style.backgroundColor = 'transparent';
            barElement.style.marginRight = '2px';
            barElement.style.display = 'inline-block';
        }
        
        container.appendChild(barElement);
    });
}

// DOM Elements
const introScreen = document.getElementById('intro-screen');
const demoScreen = document.getElementById('demo-screen');
const startDemoBtn = document.getElementById('start-demo');
const stepCounter = document.getElementById('step-counter');
const progressFill = document.getElementById('progress-fill');
const prevStepBtn = document.getElementById('prev-step');
const nextStepBtn = document.getElementById('next-step');

// Audio Elements
const scanSound = document.getElementById('scan-sound');
const passSound = document.getElementById('pass-sound');
const failSound = document.getElementById('fail-sound');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing application...');
    initializeEventListeners();
    initializeChart();
    startDateTimeUpdate(); // Start date and time updates
    
    // Initialize tower lamp to waiting state
    setTowerLampStatus('waiting');
    
    // Test verification screen
    console.log('Testing verification screen elements...');
    const testElement = document.getElementById('step-1-5');
    console.log('Step 1.5 element found:', !!testElement);
    if (testElement) {
        console.log('Step 1.5 element classes:', testElement.className);
    }
});

// Event Listeners
function initializeEventListeners() {
    // Start Demo Button
    startDemoBtn.addEventListener('click', startDemo);
    
    // Navigation Buttons
    prevStepBtn.addEventListener('click', previousStep);
    nextStepBtn.addEventListener('click', nextStep);
    
    // Step 1: Scan Barcode
    document.getElementById('scan-button').addEventListener('click', scanBarcode);
    document.getElementById('invalid-scan').addEventListener('click', invalidScan);
    
    // Step 1.5: Verification Screen
    document.getElementById('proceed-to-step2').addEventListener('click', proceedToStep2);
    
    // Step 2: Place Component
    document.getElementById('place-component').addEventListener('click', placeComponent);
    
    // Step 3: Cycle Start
    document.getElementById('cycle-start').addEventListener('click', startCycle);
    
    // Step 5: Remove Component
    document.getElementById('remove-component').addEventListener('click', removeComponent);
    
    // Step 6: Fail Sequence
    document.getElementById('move-to-rejection').addEventListener('click', moveToRejection);
    document.getElementById('submit-password').addEventListener('click', submitPassword);
    
    // Summary Report
    document.getElementById('close-summary').addEventListener('click', closeSummary);
    document.getElementById('restart-cycle').addEventListener('click', restartCycle);
    
    // Pass/Fail Modal
    document.getElementById('simulate-pass').addEventListener('click', simulatePass);
    document.getElementById('simulate-fail').addEventListener('click', simulateFail);
    
    // Password Input
    document.getElementById('password-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            submitPassword();
        }
    });
}

// Start Demo
function startDemo() {
    introScreen.classList.remove('active');
    demoScreen.classList.add('active');
    cycleData.startTime = Date.now();
    updateProgress();
    
    // Initialize barcode text
    setBarcodeText('Ready to scan...');
}

// Navigation Functions
function previousStep() {
    if (currentStep > 1) {
        currentStep--;
        showStep(currentStep);
        updateProgress();
        updateNavigationButtons();
    }
}

function nextStep() {
    // Check if trying to go to Step 4 without starting cycle
    if (currentStep === 3 && !cycleStarted) {
        alert('⚠️ Please click "Press Cycle Start" button first!');
        return;
    }
    
    if (currentStep < totalSteps) {
        currentStep++;
        showStep(currentStep);
        updateProgress();
        updateNavigationButtons();
    }
}

function showStep(stepNumber) {
    console.log('Showing step:', stepNumber);
    
    // Hide all steps
    document.querySelectorAll('.demo-step').forEach(step => {
        step.classList.remove('active');
    });
    
    // Show current step
    let stepId;
    if (stepNumber === 1.5) {
        stepId = 'step-1-5';
    } else {
        stepId = `step-${stepNumber}`;
    }
    
    console.log('Looking for step ID:', stepId);
    const stepElement = document.getElementById(stepId);
    console.log('Step element found:', !!stepElement);
    
    if (stepElement) {
        stepElement.classList.add('active');
        console.log('Step activated:', stepId);
    } else {
        console.error('Step element not found:', stepId);
    }
    
    // Update step counter
    if (stepNumber === 1.5) {
        stepCounter.textContent = `Step 1.5 of ${totalSteps}`;
    } else {
        stepCounter.textContent = `Step ${stepNumber} of ${totalSteps}`;
    }
    
    // Handle step-specific logic
    switch(stepNumber) {
        case 1:
            resetStep1();
            break;
        case 1.5:
            // Verification screen is already shown
            break;
        case 2:
            resetStep2();
            break;
        case 3:
            resetStep3();
            break;
        case 4:
            resetStep4();
            break;
        case 5:
            if (isPassSequence) {
                showPassSequence();
            }
            break;
        case 6:
            if (!isPassSequence) {
                showFailSequence();
            }
            break;
        case 7:
            // Password screen is already shown in HTML
            break;
        case 8:
            // Tool reactivation success screen is already shown in HTML
            break;
    }
}

function updateProgress() {
    let progress;
    if (currentStep === 1.5) {
        progress = (1.5 / totalSteps) * 100;
    } else {
        progress = (currentStep / totalSteps) * 100;
    }
    progressFill.style.width = `${progress}%`;
}

function updateNavigationButtons() {
    prevStepBtn.disabled = currentStep === 1;
    nextStepBtn.disabled = currentStep === totalSteps || currentStep === 1.5;
}

// Step 1: Scan Barcode
function scanBarcode() {
    console.log('Scan barcode function called');
    
    const scanResult = document.getElementById('scan-result');
    const stepStatus = document.getElementById('step1-status');
    
    // Generate random barcode
    const barcode = 'ABC' + Math.floor(Math.random() * 10000).toString().padStart(4, '0');
    cycleData.barcode = barcode;
    
    console.log('Generated barcode:', barcode);
    
    // Play scan sound
    playSound(scanSound);
    
    // Update display using the dedicated function
    setBarcodeText(barcode);
    stepStatus.textContent = '✅ Complete';
    stepStatus.style.background = '#d4edda';
    stepStatus.style.color = '#155724';
    
    // Show success result
    scanResult.innerHTML = '✅ Scan OK — Part Selected in Nutrunner';
    scanResult.className = 'result-display success';
    
    // Set tower lamp to green (success)
    setTowerLampStatus('success');
    
    console.log('Will show verification screen in 1.5 seconds');
    
    // Show verification screen after delay
    setTimeout(() => {
        showVerificationScreen(barcode);
    }, 1500);
}

function invalidScan() {
    const scanResult = document.getElementById('scan-result');
    const stepStatus = document.getElementById('step1-status');
    
    // Play error sound
    playSound(failSound);
    
    // Update display
    stepStatus.textContent = '❌ Error';
    stepStatus.style.background = '#f8d7da';
    stepStatus.style.color = '#721c24';
    
    // Show error result
    scanResult.innerHTML = '❌ Invalid Barcode — Try Again';
    scanResult.className = 'result-display error';
    
    // Set tower lamp to red (error)
    setTowerLampStatus('error');
    
    // Reset after 2 seconds
    setTimeout(() => {
        resetStep1();
    }, 2000);
}

function resetStep1() {
    const scanResult = document.getElementById('scan-result');
    const stepStatus = document.getElementById('step1-status');
    
    // Clear scan result
    scanResult.innerHTML = '';
    scanResult.className = 'result-display';
    
    // Reset barcode text to initial state using the dedicated function
    setBarcodeText('Ready to scan...');
    
    // Reset step status
    stepStatus.textContent = '⏳ Waiting...';
    stepStatus.style.background = '#fff3cd';
    stepStatus.style.color = '#856404';
    
    // Set tower lamp to orange (waiting)
    setTowerLampStatus('waiting');
}

// Step 1.5: Verification Screen
function showVerificationScreen(barcode) {
    console.log('Showing verification screen with barcode:', barcode);
    
    // Update step counter to show Step 1.5
    currentStep = 1.5;
    showStep(1.5);
    updateProgress();
    updateNavigationButtons();
    
    // Update verification display
    const scannedBarcodeDisplay = document.getElementById('scanned-barcode-display');
    const controllerPartDisplay = document.getElementById('controller-part-display');
    const stepStatus = document.getElementById('step1-5-status');
    
    console.log('Elements found:', {
        scannedBarcodeDisplay: !!scannedBarcodeDisplay,
        controllerPartDisplay: !!controllerPartDisplay,
        stepStatus: !!stepStatus
    });
    
    // Set scanned data to actual barcode
    if (scannedBarcodeDisplay) {
        scannedBarcodeDisplay.textContent = barcode;
    }
    
    // Set controller part to M8-NUT-{barcode}
    if (controllerPartDisplay) {
        controllerPartDisplay.textContent = 'M8-NUT-' + barcode;
    }
    
    if (stepStatus) {
        stepStatus.textContent = '✅ Verification Complete';
        stepStatus.style.background = '#d4edda';
        stepStatus.style.color = '#155724';
    }
}

function proceedToStep2() {
    // Move to Step 2
    currentStep = 2;
    showStep(2);
    updateProgress();
    updateNavigationButtons();
}

// Tower Lamp Control Function
function setTowerLampStatus(status) {
    const redLight = document.getElementById('red-light');
    const orangeLight = document.getElementById('orange-light');
    const greenLight = document.getElementById('green-light');
    
    // Remove active class from all lights
    redLight.classList.remove('active');
    orangeLight.classList.remove('active');
    greenLight.classList.remove('active');
    
    // Activate the appropriate light based on status
    switch(status) {
        case 'waiting':
            orangeLight.classList.add('active');
            break;
        case 'success':
            greenLight.classList.add('active');
            break;
        case 'error':
            redLight.classList.add('active');
            break;
        default:
            orangeLight.classList.add('active');
    }
}

// Step 2: Place Component
function placeComponent() {
    const componentPlaceholder = document.querySelector('.component-placeholder');
    const partSensor = document.getElementById('part-sensor');
    const stepStatus = document.getElementById('step2-status');
    
    // Update component area
    componentPlaceholder.classList.add('has-component');
    componentPlaceholder.querySelector('span').textContent = 'Component Placed';
    
    // Update sensor status
    partSensor.textContent = '✅ OK';
    partSensor.className = 'sensor-value ok';
    
    // Update step status
    stepStatus.textContent = '✅ Complete';
    stepStatus.style.background = '#d4edda';
    stepStatus.style.color = '#155724';
    
    // Enable next step
    setTimeout(() => {
        nextStep();
    }, 1000);
}

function resetStep2() {
    const componentPlaceholder = document.querySelector('.component-placeholder');
    const partSensor = document.getElementById('part-sensor');
    const stepStatus = document.getElementById('step2-status');
    
    componentPlaceholder.classList.remove('has-component');
    componentPlaceholder.querySelector('span').textContent = 'Place Component Here';
    partSensor.textContent = '❌ Not Detected';
    partSensor.className = 'sensor-value not-detected';
    stepStatus.textContent = '⏳ Waiting...';
    stepStatus.style.background = '#fff3cd';
    stepStatus.style.color = '#856404';
}

// Step 3: Press Cycle Start
function startCycle() {
    const pneumaticPiston = document.getElementById('pneumatic-piston');
    const cylinderStatus = document.getElementById('cylinder-status');
    const reedIndicator = document.getElementById('reed-indicator');
    const stepStatus = document.getElementById('step3-status');
    const blinkMessage = document.querySelector('.blink-message');
    
    // Set cycle started flag
    cycleStarted = true;
    
    // Hide blinking message
    if (blinkMessage) {
        blinkMessage.style.display = 'none';
    }
    
    // Animate cylinder forward
    setTimeout(() => {
        pneumaticPiston.classList.add('extended');
        cylinderStatus.textContent = 'Extended';
    }, 300);
    
    // Update reed switch
    setTimeout(() => {
        reedIndicator.textContent = '🟢';
        reedIndicator.classList.add('active');
    }, 800);
    
    // Update step status
    stepStatus.textContent = '✅ Complete';
    stepStatus.style.background = '#d4edda';
    stepStatus.style.color = '#155724';
    
    // Auto advance to next step
    setTimeout(() => {
        nextStep();
    }, 1500);
}

function resetStep3() {
    const pneumaticPiston = document.getElementById('pneumatic-piston');
    const cylinderStatus = document.getElementById('cylinder-status');
    const reedIndicator = document.getElementById('reed-indicator');
    const stepStatus = document.getElementById('step3-status');
    const blinkMessage = document.querySelector('.blink-message');
    
    // Reset cycle started flag
    cycleStarted = false;
    
    pneumaticPiston.classList.remove('extended');
    cylinderStatus.textContent = 'Retracted';
    reedIndicator.textContent = '🔴';
    reedIndicator.classList.remove('active');
    stepStatus.textContent = '⏳ Waiting...';
    stepStatus.style.background = '#fff3cd';
    stepStatus.style.color = '#856404';
    
    // Show blinking message again
    if (blinkMessage) {
        blinkMessage.style.display = 'inline-block';
    }
}

// Step 4: Tightening Process
function resetStep4() {
    const stepStatus = document.getElementById('step4-status');
    const tighteningResult = document.getElementById('tightening-result');
    
    // Reset chart
    resetChart();
    
    // Reset metrics
    document.getElementById('current-torque').textContent = '0.0 Nm';
    document.getElementById('current-angle').textContent = '0°';
    
    // Reset result display
    tighteningResult.innerHTML = '';
    tighteningResult.className = 'result-display';
    
    // Update step status
    stepStatus.textContent = '⏳ Waiting...';
    stepStatus.style.background = '#fff3cd';
    stepStatus.style.color = '#856404';
    
    // Start tightening process
    setTimeout(() => {
        startTighteningProcess();
    }, 1000);
}

function startTighteningProcess() {
    const stepStatus = document.getElementById('step4-status');
    const tighteningResult = document.getElementById('tightening-result');
    
    stepStatus.textContent = '⚡ Processing...';
    stepStatus.style.background = '#cce5ff';
    stepStatus.style.color = '#004085';
    
    // Reset values
    currentTorque = 0;
    currentAngle = 0;
    
    // Start updating chart and metrics
    tighteningInterval = setInterval(() => {
        // Simulate torque and angle increase
        currentTorque += Math.random() * 2 + 0.5;
        currentAngle += Math.random() * 3 + 1;
        
        // Update display
        document.getElementById('current-torque').textContent = `${currentTorque.toFixed(1)} Nm`;
        document.getElementById('current-angle').textContent = `${Math.round(currentAngle)}°`;
        
        // Update chart
        updateChart(currentTorque, currentAngle);
        
        // Check if tightening is complete
        if (currentTorque >= 25.0 && currentAngle >= 90) {
            clearInterval(tighteningInterval);
            completeTightening();
        }
    }, 100);
}

function completeTightening() {
    const stepStatus = document.getElementById('step4-status');
    const tighteningResult = document.getElementById('tightening-result');
    
    // Update final values
    cycleData.finalTorque = currentTorque;
    cycleData.finalAngle = Math.round(currentAngle);
    
    // Show popup for user to choose pass/fail simulation
    showPassFailModal();
}

function showPassFailModal() {
    const modal = document.getElementById('pass-fail-modal');
    modal.classList.remove('hidden');
}

function hidePassFailModal() {
    const modal = document.getElementById('pass-fail-modal');
    modal.classList.add('hidden');
}

function simulatePass() {
    const stepStatus = document.getElementById('step4-status');
    const tighteningResult = document.getElementById('tightening-result');
    
    isPassSequence = true;
    cycleData.result = 'PASS';
    
    // Pass result
    playSound(passSound);
    stepStatus.textContent = '✅ Complete';
    stepStatus.style.background = '#d4edda';
    stepStatus.style.color = '#155724';
    tighteningResult.innerHTML = '✅ PASS - All specifications met';
    tighteningResult.className = 'result-display success';
    
    hidePassFailModal();
    
    // Show blinking message for 5 seconds
    showBlinkingMessage();
    
    // Auto advance to next step after 5 seconds
    setTimeout(() => {
        nextStep();
    }, 5000);
}

function showBlinkingMessage() {
    const tighteningResult = document.getElementById('tightening-result');
    
    // Show blinking message
    tighteningResult.innerHTML = '🔄 Reverse Disable Confirmed';
    tighteningResult.className = 'result-display blinking';
    
    // Remove blinking class after 5 seconds
    setTimeout(() => {
        tighteningResult.innerHTML = '✅ PASS - All specifications met';
        tighteningResult.className = 'result-display success';
    }, 5000);
}

function simulateFail() {
    const stepStatus = document.getElementById('step4-status');
    const tighteningResult = document.getElementById('tightening-result');
    
    isPassSequence = false;
    cycleData.result = 'FAIL';
    
    // Fail result
    playSound(failSound);
    stepStatus.textContent = '❌ Failed';
    stepStatus.style.background = '#f8d7da';
    stepStatus.style.color = '#721c24';
    tighteningResult.innerHTML = '❌ FAIL - Specifications not met';
    tighteningResult.className = 'result-display error';
    
    hidePassFailModal();
    
    // Go directly to Step 6 (Fail Sequence) instead of Step 5
    setTimeout(() => {
        currentStep = 6;
        showStep(6);
        updateProgress();
        updateNavigationButtons();
    }, 2000);
}

// Chart Functions
function initializeChart() {
    const ctx = document.getElementById('torque-chart').getContext('2d');
    torqueChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Torque (Nm)',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }, {
                label: 'Angle (degrees)',
                data: [],
                borderColor: '#764ba2',
                backgroundColor: 'rgba(118, 75, 162, 0.2)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                yAxisID: 'y1',
                pointBackgroundColor: '#764ba2',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Time (s)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        color: '#2c3e50'
                    },
                    grid: {
                        color: 'rgba(135, 206, 235, 0.2)',
                        lineWidth: 1
                    },
                    ticks: {
                        color: '#495057',
                        font: {
                            size: 12
                        }
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Torque (Nm)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        color: '#667eea'
                    },
                    min: 0,
                    max: 30,
                    grid: {
                        color: 'rgba(135, 206, 235, 0.2)',
                        lineWidth: 1
                    },
                    ticks: {
                        color: '#495057',
                        font: {
                            size: 12
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Angle (degrees)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        color: '#764ba2'
                    },
                    min: 0,
                    max: 120,
                    grid: {
                        drawOnChartArea: false,
                        color: 'rgba(135, 206, 235, 0.2)',
                        lineWidth: 1
                    },
                    ticks: {
                        color: '#495057',
                        font: {
                            size: 12
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        color: '#2c3e50'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    titleColor: '#2c3e50',
                    bodyColor: '#495057',
                    borderColor: '#667eea',
                    borderWidth: 2,
                    cornerRadius: 8,
                    displayColors: true,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    }
                }
            }
        }
    });
}

function updateChart(torque, angle) {
    const timePoint = torqueChart.data.labels.length;
    
    torqueChart.data.labels.push(timePoint);
    torqueChart.data.datasets[0].data.push(torque);
    torqueChart.data.datasets[1].data.push(angle);
    
    // Keep only last 50 points for performance
    if (torqueChart.data.labels.length > 50) {
        torqueChart.data.labels.shift();
        torqueChart.data.datasets[0].data.shift();
        torqueChart.data.datasets[1].data.shift();
    }
    
    torqueChart.update('none');
}

function resetChart() {
    torqueChart.data.labels = [];
    torqueChart.data.datasets[0].data = [];
    torqueChart.data.datasets[1].data = [];
    torqueChart.update();
}

// Step 5: Pass Sequence
function showPassSequence() {
    const passCylinderPiston = document.getElementById('pass-cylinder-piston');
    const passCylinderStatus = document.getElementById('pass-cylinder-status');
    const stepStatus = document.getElementById('step5-status');
    
    // Animate cylinder retraction
    passCylinderPiston.classList.add('extended');
    setTimeout(() => {
        passCylinderPiston.classList.remove('extended');
        passCylinderStatus.textContent = 'Retracted';
    }, 1000);
    
    // Update step status
    stepStatus.textContent = '✅ Complete';
    stepStatus.style.background = '#d4edda';
    stepStatus.style.color = '#155724';
}

function removeComponent() {
    // Show summary report
    showSummaryReport();
}

// Step 6: Fail Sequence
function showFailSequence() {
    const stepStatus = document.getElementById('step6-status');
    stepStatus.textContent = '⏳ Starting Fail Sequence...';
    stepStatus.style.background = '#fff3cd';
    stepStatus.style.color = '#856404';
    
    // Start the fail sequence automatically
    startFailSequence();
}

function startFailSequence() {
    const statusText = document.getElementById('fail-status-text');
    const statusMessage = document.getElementById('fail-status-message');
    const stepStatus = document.getElementById('step6-status');
    
    // Initial status
    stepStatus.textContent = '🔄 Fail Sequence Started';
    stepStatus.style.background = '#fff3cd';
    stepStatus.style.color = '#856404';
    
    // Message 1: Part Clamp Reversing
    statusText.textContent = '🔄 Part Clamp Reversing...';
    statusMessage.className = 'status-message updating';
    
    // After 2 seconds: Part Clamp Reverse Reed Switch OK (reduced from 5 seconds)
    setTimeout(() => {
        statusText.textContent = '✅ Part Clamp Reverse Reed Switch OK';
        statusMessage.className = 'status-message success';
    }, 2000);
    
    // After 2 more seconds (4 total): Move Component Sensor to Rejection Bin (reduced from 8 seconds)
    setTimeout(() => {
        statusText.textContent = '📦 Move Component Sensor to Rejection Bin';
        statusMessage.className = 'status-message updating';
    }, 4000);
    
    // After 2 more seconds (6 total): Rejection Bin Sensor Sensed (reduced from 11 seconds)
    setTimeout(() => {
        statusText.textContent = '✅ Rejection Bin Sensor Sensed';
        statusMessage.className = 'status-message success';
        
        // Hide rejection bin image and show password section
        setTimeout(() => {
            hideRejectionBinAndShowPassword();
        }, 1500); // Reduced from 2000ms
    }, 6000);
}

function hideRejectionBinAndShowPassword() {
    const rejectionSection = document.getElementById('rejection-section');
    const statusText = document.getElementById('fail-status-text');
    const statusMessage = document.getElementById('fail-status-message');
    const stepStatus = document.getElementById('step6-status');
    
    // Hide rejection bin section
    rejectionSection.style.display = 'none';
    
    // Update status
    statusText.textContent = '🔒 Moving to Tool Reactivation Screen';
    statusMessage.className = 'status-message updating';
    
    stepStatus.textContent = '✅ Rejection Complete - Tool Locked';
    stepStatus.style.background = '#f8d7da';
    stepStatus.style.color = '#721c24';
    
    // Advance to Step 7 (Password Screen) after delay
    setTimeout(() => {
        currentStep = 7;
        showStep(7);
        updateProgress();
        updateNavigationButtons();
    }, 2000);
}

function moveToRejection() {
    const rejectionSensor = document.getElementById('rejection-sensor');
    const stepStatus = document.getElementById('step6-status');
    
    // Update rejection sensor
    rejectionSensor.textContent = '✅ Triggered';
    rejectionSensor.style.background = '#d4edda';
    rejectionSensor.style.color = '#155724';
    
    // Update step status
    stepStatus.textContent = '⏳ Rejection Bin Sensing...';
    stepStatus.style.background = '#fff3cd';
    stepStatus.style.color = '#856404';
    
    // The status bar will automatically update after 3 seconds (11 total seconds from start)
    // This function is now just for the sensor update
}

function submitPassword() {
    const passwordInput = document.getElementById('password-input');
    const password = passwordInput.value;
    const stepStatus = document.getElementById('step7-status');
    const statusText = document.getElementById('reactivation-status-text');
    const statusMessage = document.getElementById('reactivation-status-message');
    
    if (password === '1234') { // Demo password
        // Password correct - show success
        stepStatus.textContent = '✅ Password Accepted - Tool Activated';
        stepStatus.style.background = '#d4edda';
        stepStatus.style.color = '#155724';
        
        statusText.textContent = '🔓 Tool Successfully Reactivated';
        statusMessage.className = 'status-message success';
        
        // Clear password input
        passwordInput.value = '';
        
        // Show success message and then show reactivation success screen
        setTimeout(() => {
            showReactivationSuccessScreen();
        }, 2000);
    } else {
        // Show error
        passwordInput.style.borderColor = '#dc3545';
        passwordInput.style.boxShadow = '0 0 0 3px rgba(220, 53, 69, 0.1)';
        
        statusText.textContent = '❌ Incorrect Password - Try Again';
        statusMessage.className = 'status-message error';
        
        // Reset after 2 seconds
        setTimeout(() => {
            passwordInput.style.borderColor = '#dee2e6';
            passwordInput.style.boxShadow = 'none';
            passwordInput.value = '';
            statusText.textContent = '⏳ Waiting for password...';
            statusMessage.className = 'status-message';
        }, 2000);
    }
}

function showReactivationSuccessScreen() {
    // Move to Step 8 (Tool Reactivation Success)
    currentStep = 8;
    showStep(8);
    updateProgress();
    updateNavigationButtons();
    
    // Auto advance to step 1 (barcode scan) after delay
    setTimeout(() => {
        currentStep = 1;
        showStep(1);
        updateProgress();
        updateNavigationButtons();
        setBarcodeText('Ready to scan...');
    }, 4000);
}

function showRemoveComponentMessage() {
    const stepStatus = document.getElementById('step6-status');
    const statusText = document.getElementById('fail-status-text');
    const statusMessage = document.getElementById('fail-status-message');
    
    // Show "Remove Component" message
    stepStatus.textContent = '📦 Component Removed';
    stepStatus.style.background = '#d4edda';
    stepStatus.style.color = '#155724';
    
    statusText.textContent = '🔄 Ready for new cycle - Please scan barcode';
    statusMessage.className = 'status-message updating';
    
    // Auto advance to step 1 (barcode scan) after delay
    setTimeout(() => {
        currentStep = 1;
        showStep(1);
        updateProgress();
        updateNavigationButtons();
        setBarcodeText('Ready to scan...');
    }, 3000);
}

function showFailResults() {
    const stepStatus = document.getElementById('step6-status');
    const resetMessage = document.getElementById('reset-tool-message');
    
    // Show fail results
    stepStatus.textContent = '❌ FAIL - Component rejected';
    stepStatus.style.background = '#f8d7da';
    stepStatus.style.color = '#721c24';
    
    resetMessage.textContent = '📱 Please scan barcode to start new cycle';
    resetMessage.style.color = '#856404';
    resetMessage.style.background = '#fff3cd';
    resetMessage.style.borderColor = '#ffeaa7';
    
    // Auto advance to step 1 (barcode scan) after delay
    setTimeout(() => {
        currentStep = 1;
        showStep(1);
        updateProgress();
        updateNavigationButtons();
        setBarcodeText('Ready to scan...');
    }, 3000);
}

// Summary Report
function showSummaryReport() {
    const summaryReport = document.getElementById('summary-report');
    
    // Calculate cycle time
    cycleData.cycleTime = ((Date.now() - cycleData.startTime) / 1000).toFixed(1);
    
    // Update summary data
    document.getElementById('summary-barcode').textContent = cycleData.barcode;
    document.getElementById('summary-torque').textContent = `${cycleData.finalTorque.toFixed(1)} Nm`;
    document.getElementById('summary-angle').textContent = `${cycleData.finalAngle}°`;
    document.getElementById('summary-result').textContent = cycleData.result;
    document.getElementById('summary-time').textContent = `${cycleData.cycleTime}s`;
    
    // Show summary
    summaryReport.classList.remove('hidden');
}

function closeSummary() {
    document.getElementById('summary-report').classList.add('hidden');
}

function restartCycle() {
    // Reset all data
    cycleData = {
        barcode: '',
        finalTorque: 0,
        finalAngle: 0,
        result: '',
        cycleTime: 0,
        startTime: Date.now()
    };
    
    // Reset cycle started flag
    cycleStarted = false;
    
    // Reset to step 1
    currentStep = 1;
    showStep(1);
    updateProgress();
    updateNavigationButtons();
    
    // Close summary
    closeSummary();
    
    // Reset barcode text
    setBarcodeText('Ready to scan...');
    
    // Toggle pass/fail for variety
    isPassSequence = Math.random() > 0.3;
}

// Utility Functions
function playSound(audioElement) {
    if (audioElement) {
        audioElement.currentTime = 0;
        audioElement.play().catch(e => console.log('Audio play failed:', e));
    }
}

// Add some visual feedback for sensor status
function updateSensorStatus(sensorId, status, isOK) {
    const sensor = document.getElementById(sensorId);
    if (sensor) {
        sensor.textContent = isOK ? '✅ OK' : '❌ Not Detected';
        sensor.style.background = isOK ? '#d4edda' : '#f8d7da';
        sensor.style.color = isOK ? '#155724' : '#721c24';
    }
}

// Add keyboard shortcuts for demo
document.addEventListener('keydown', function(e) {
    switch(e.key) {
        case 'ArrowLeft':
            if (!prevStepBtn.disabled) previousStep();
            break;
        case 'ArrowRight':
            if (!nextStepBtn.disabled) nextStep();
            break;
        case 'Enter':
            if (currentStep === 1) scanBarcode();
            else if (currentStep === 2) placeComponent();
            else if (currentStep === 3) startCycle();
            break;
    }
});

// Add touch support for mobile
let touchStartX = 0;
let touchEndX = 0;

document.addEventListener('touchstart', function(e) {
    touchStartX = e.changedTouches[0].screenX;
});

document.addEventListener('touchend', function(e) {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
});

function handleSwipe() {
    const swipeThreshold = 50;
    const diff = touchStartX - touchEndX;
    
    if (Math.abs(diff) > swipeThreshold) {
        if (diff > 0 && !nextStepBtn.disabled) {
            // Swipe left - next step
            nextStep();
        } else if (diff < 0 && !prevStepBtn.disabled) {
            // Swipe right - previous step
            previousStep();
        }
    }
}

// Date and Time Functions
function updateDateTime() {
    const now = new Date();
    
    // Update date
    const dateElement = document.getElementById('current-date');
    if (dateElement) {
        const options = { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        };
        dateElement.textContent = now.toLocaleDateString('en-US', options);
    }
    
    // Update time
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const timeOptions = { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: true 
        };
        timeElement.textContent = now.toLocaleTimeString('en-US', timeOptions);
    }
}

function startDateTimeUpdate() {
    // Update immediately
    updateDateTime();
    
    // Update every second
    dateTimeInterval = setInterval(updateDateTime, 1000);
}

function stopDateTimeUpdate() {
    if (dateTimeInterval) {
        clearInterval(dateTimeInterval);
    }
} 

 

 
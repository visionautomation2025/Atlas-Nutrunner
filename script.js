// Global variables
let currentWorkflowStep = 1;
let isWorkflowRunning = false;
let toolStatuses = ['ready', 'running', 'complete', 'error'];
let currentToolIndex = 0;

// Navigation functionality
document.addEventListener('DOMContentLoaded', function() {
    // Navigation
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.demo-section');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            
            // Update active nav link
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Show target section
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === targetId) {
                    section.classList.add('active');
                }
            });
        });
    });

    // Initialize charts
    initializeCharts();
});

// 1. Open Protocol Communication Overview Functions

function startFlowchartAnimation() {
    const devices = document.querySelectorAll('.device');
    const connectionLines = document.querySelector('.connection-lines');
    
    // Animate devices
    devices.forEach((device, index) => {
        setTimeout(() => {
            device.classList.add('animate');
        }, index * 500);
    });
    
    // Animate connection lines
    setTimeout(() => {
        connectionLines.style.display = 'block';
    }, 2000);
    
    // Stop animation after 5 seconds
    setTimeout(() => {
        devices.forEach(device => device.classList.remove('animate'));
        connectionLines.style.display = 'none';
    }, 5000);
}

function startPacketAnimation() {
    const packets = document.querySelectorAll('.packet');
    
    packets.forEach((packet, index) => {
        setTimeout(() => {
            packet.classList.add('animate');
        }, index * 1000);
    });
    
    setTimeout(() => {
        packets.forEach(packet => packet.classList.remove('animate'));
    }, 6000);
}

function simulateBarcodeScan() {
    const jobItems = document.querySelectorAll('.job-item');
    const ackText = document.querySelector('.ack-text');
    
    // Randomly select a job
    const randomJob = jobItems[Math.floor(Math.random() * jobItems.length)];
    const jobId = randomJob.getAttribute('data-job');
    
    // Highlight selected job
    jobItems.forEach(item => item.classList.remove('selected'));
    randomJob.classList.add('selected');
    
    // Update acknowledgment
    ackText.textContent = `Job ${jobId} selected and acknowledged!`;
    ackText.style.color = '#38a169';
    
    // Reset after 3 seconds
    setTimeout(() => {
        randomJob.classList.remove('selected');
        ackText.textContent = 'Waiting for scan...';
        ackText.style.color = '#4a5568';
    }, 3000);
}

// 2. Integration Functions

function triggerBarcodeScan() {
    const barcode = document.getElementById('demoBarcode');
    const loadingProgress = document.querySelector('.loading-progress');
    const loadingText = document.querySelector('.loading-text');
    const jobLoaded = document.querySelector('.job-loaded');
    
    // Generate random barcode
    const newBarcode = Math.floor(Math.random() * 900000000) + 100000000;
    barcode.textContent = newBarcode;
    
    // Show loading animation
    loadingProgress.classList.add('animate');
    loadingText.textContent = 'Loading job...';
    
    // Simulate job loading
    setTimeout(() => {
        loadingProgress.classList.remove('animate');
        loadingText.textContent = 'Job loaded successfully!';
        jobLoaded.classList.add('show');
        
        setTimeout(() => {
            jobLoaded.classList.remove('show');
            loadingText.textContent = 'Ready for next scan';
        }, 2000);
    }, 2000);
}

function sendPLCSignal(signal) {
    const signalArrow = document.querySelector('.signal-arrow');
    const responseIndicator = document.querySelector('.response-indicator');
    const responseText = document.querySelector('.response-text');
    
    // Animate signal flow
    signalArrow.classList.add('animate');
    
    setTimeout(() => {
        signalArrow.classList.remove('animate');
        
        // Update response based on signal
        if (signal === 'START') {
            responseIndicator.classList.add('success');
            responseText.textContent = 'PF6000 started successfully';
        } else {
            responseIndicator.classList.add('error');
            responseText.textContent = 'PF6000 stopped';
        }
        
        // Reset after 3 seconds
        setTimeout(() => {
            responseIndicator.classList.remove('success', 'error');
            responseText.textContent = 'Waiting for signal...';
        }, 3000);
    }, 1000);
}

function updateToolStatus() {
    const toolStatuses = document.querySelectorAll('.tool-status');
    
    toolStatuses.forEach((tool, index) => {
        setTimeout(() => {
            // Remove all status classes
            tool.classList.remove('ready', 'running', 'complete', 'error');
            
            // Add new random status
            const statuses = ['ready', 'running', 'complete', 'error'];
            const newStatus = statuses[Math.floor(Math.random() * statuses.length)];
            tool.classList.add(newStatus);
            
            // Update text
            const statusText = tool.querySelector('span');
            statusText.textContent = `Tool ${index + 1}: ${newStatus.charAt(0).toUpperCase() + newStatus.slice(1)}`;
        }, index * 500);
    });
}

// 3. Customization Functions

function deployToAllTools() {
    const progressFill = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    const toolItems = document.querySelectorAll('.tool-item');
    const deployBtn = document.querySelector('.deploy-btn');
    
    // Disable button during deployment
    deployBtn.disabled = true;
    deployBtn.textContent = 'Deploying...';
    
    // Animate progress bar
    let progress = 0;
    const interval = setInterval(() => {
        progress += 2;
        progressFill.style.width = progress + '%';
        progressText.textContent = progress + '%';
        
        if (progress >= 100) {
            clearInterval(interval);
            
            // Deploy to each tool
            toolItems.forEach((tool, index) => {
                setTimeout(() => {
                    tool.classList.add('deployed');
                    tool.textContent = 'Deployed ✓';
                }, index * 200);
            });
            
            // Reset after 3 seconds
            setTimeout(() => {
                toolItems.forEach(tool => {
                    tool.classList.remove('deployed');
                    tool.textContent = tool.getAttribute('data-tool') === '1' ? 'Tool 1' : 
                                     tool.getAttribute('data-tool') === '2' ? 'Tool 2' : 
                                     tool.getAttribute('data-tool') === '3' ? 'Tool 3' : 'Tool 4';
                });
                progressFill.style.width = '0%';
                progressText.textContent = '0%';
                deployBtn.disabled = false;
                deployBtn.innerHTML = '<i class="fas fa-rocket"></i> Deploy to All Tools';
            }, 3000);
        }
    }, 50);
}

function testToolAccess() {
    const barcodeRequired = document.getElementById('barcodeRequired').checked;
    const operatorAuth = document.getElementById('operatorAuth').checked;
    const qualityCheck = document.getElementById('qualityCheck').checked;
    const accessResult = document.querySelector('.access-result');
    const resultText = document.querySelector('.result-text');
    
    // Simulate access check
    setTimeout(() => {
        let allowed = true;
        let message = 'Access granted';
        
        if (barcodeRequired && !hasBarcodeScanned()) {
            allowed = false;
            message = 'Barcode scan required';
        } else if (operatorAuth && !hasOperatorAuth()) {
            allowed = false;
            message = 'Operator authentication required';
        } else if (qualityCheck && !hasQualityCheck()) {
            allowed = false;
            message = 'Quality check failed';
        }
        
        // Update result display
        accessResult.classList.remove('allowed', 'blocked');
        accessResult.classList.add(allowed ? 'allowed' : 'blocked');
        resultText.textContent = message;
        
        // Reset after 3 seconds
        setTimeout(() => {
            accessResult.classList.remove('allowed', 'blocked');
            resultText.textContent = 'Click to test access rules';
        }, 3000);
    }, 1000);
}

function saveConfiguration() {
    const torqueTarget = document.getElementById('torqueTarget').value;
    const angleTarget = document.getElementById('angleTarget').value;
    const tolerance = document.getElementById('tolerance').value;
    const saveBtn = document.querySelector('.save-btn');
    
    // Show saving animation
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    saveBtn.disabled = true;
    
    // Simulate save process
    setTimeout(() => {
        saveBtn.innerHTML = '<i class="fas fa-check"></i> Saved!';
        saveBtn.style.background = '#38a169';
        
        // Show configuration summary
        showNotification(`Configuration saved: Torque ${torqueTarget}Nm, Angle ${angleTarget}°, Tolerance ${tolerance}%`);
        
        // Reset button after 2 seconds
        setTimeout(() => {
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Configuration';
            saveBtn.style.background = '#38a169';
            saveBtn.disabled = false;
        }, 2000);
    }, 1500);
}

// 4. System Integration Functions

function startDataFlow() {
    const dataPackets = document.querySelectorAll('.data-packet');
    const systems = document.querySelectorAll('.system');
    
    // Animate data packets
    dataPackets.forEach((packet, index) => {
        setTimeout(() => {
            packet.classList.add('animate');
        }, index * 800);
    });
    
    // Animate systems
    systems.forEach((system, index) => {
        setTimeout(() => {
            system.style.transform = 'scale(1.1)';
            system.style.boxShadow = '0 8px 25px rgba(102, 126, 234, 0.3)';
        }, index * 1000);
    });
    
    // Reset animations
    setTimeout(() => {
        dataPackets.forEach(packet => packet.classList.remove('animate'));
        systems.forEach(system => {
            system.style.transform = 'scale(1)';
            system.style.boxShadow = 'none';
        });
    }, 5000);
}

function addDatabaseEntry() {
    const dbRows = document.querySelector('.db-rows');
    const jobIds = ['JOB001', 'JOB002', 'JOB003', 'JOB004', 'JOB005'];
    const torques = ['52.3', '48.7', '51.2', '49.8', '53.1'];
    const angles = ['87.2', '89.5', '86.8', '90.1', '88.3'];
    const results = ['OK', 'OK', 'NOT OK', 'OK', 'OK'];
    
    const randomIndex = Math.floor(Math.random() * jobIds.length);
    
    const newRow = document.createElement('div');
    newRow.className = 'db-row new-entry';
    newRow.innerHTML = `
        <span>${jobIds[randomIndex]}</span>
        <span>${torques[randomIndex]} Nm</span>
        <span>${angles[randomIndex]}°</span>
        <span class="${results[randomIndex] === 'OK' ? 'success' : 'error'}">${results[randomIndex]}</span>
    `;
    
    dbRows.appendChild(newRow);
    
    // Remove new-entry class after animation
    setTimeout(() => {
        newRow.classList.remove('new-entry');
    }, 500);
    
    // Limit rows to 5
    if (dbRows.children.length > 5) {
        dbRows.removeChild(dbRows.firstChild);
    }
}

function uploadReports() {
    const reportItems = document.querySelectorAll('.report-item');
    const uploadFill = document.querySelector('.upload-fill');
    const uploadText = document.querySelector('.upload-text');
    const serverSync = document.querySelector('.server-sync');
    
    // Animate each report upload
    reportItems.forEach((item, index) => {
        setTimeout(() => {
            item.classList.add('uploading');
            item.innerHTML += ' <i class="fas fa-spinner fa-spin"></i>';
        }, index * 1000);
        
        setTimeout(() => {
            item.classList.remove('uploading');
            item.classList.add('completed');
            item.innerHTML = item.innerHTML.replace('<i class="fas fa-spinner fa-spin"></i>', '<i class="fas fa-check"></i>');
        }, (index + 1) * 1000);
    });
    
    // Animate progress bar
    let progress = 0;
    const interval = setInterval(() => {
        progress += 1;
        uploadFill.style.width = progress + '%';
        uploadText.textContent = `Uploading... ${progress}%`;
        
        if (progress >= 100) {
            clearInterval(interval);
            uploadText.textContent = 'Upload complete!';
            serverSync.style.background = '#f0fff4';
            serverSync.style.border = '2px solid #9ae6b4';
            
            // Reset after 3 seconds
            setTimeout(() => {
                reportItems.forEach(item => {
                    item.classList.remove('completed');
                    item.innerHTML = item.innerHTML.replace('<i class="fas fa-check"></i>', '');
                });
                uploadFill.style.width = '0%';
                uploadText.textContent = 'Ready to upload';
                serverSync.style.background = '#f7fafc';
                serverSync.style.border = 'none';
            }, 3000);
        }
    }, 30);
}

// 5. Analytics Functions

function startDataProcessing() {
    const dataPoints = document.querySelectorAll('.data-point');
    const pipelineStages = document.querySelectorAll('.pipeline-stage');
    
    // Animate data points
    dataPoints.forEach((point, index) => {
        setTimeout(() => {
            point.classList.add('animate');
        }, index * 500);
    });
    
    // Animate pipeline stages
    pipelineStages.forEach((stage, index) => {
        setTimeout(() => {
            stage.classList.add('active');
        }, index * 1000);
    });
    
    // Reset animations
    setTimeout(() => {
        dataPoints.forEach(point => point.classList.remove('animate'));
        pipelineStages.forEach(stage => stage.classList.remove('active'));
    }, 4000);
}

function updateAnalytics() {
    // Update torque chart
    updateTorqueChart();
    
    // Update failure rate
    updateFailureRate();
    
    // Update heatmap
    updateHeatmap();
    
    showNotification('Analytics updated with latest data');
}

function triggerAlert() {
    const alertItems = document.querySelectorAll('.alert-item');
    const alertHistory = document.querySelector('.alert-history');
    
    // Randomly select an alert to trigger
    const randomAlert = alertItems[Math.floor(Math.random() * alertItems.length)];
    randomAlert.classList.add('animate');
    
    // Add to history
    const timestamp = new Date().toLocaleTimeString();
    const alertText = randomAlert.querySelector('span').textContent;
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    historyItem.textContent = `${timestamp} - ${alertText}`;
    
    alertHistory.insertBefore(historyItem, alertHistory.firstChild);
    
    // Remove animation class
    setTimeout(() => {
        randomAlert.classList.remove('animate');
    }, 500);
    
    // Limit history items
    if (alertHistory.children.length > 5) {
        alertHistory.removeChild(alertHistory.lastChild);
    }
}

// 6. ROI Functions

function updateROIChart() {
    const canvas = document.getElementById('roiChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw ROI chart
    ctx.fillStyle = '#667eea';
    ctx.fillRect(20, height - 60, 40, 60);
    
    ctx.fillStyle = '#38a169';
    ctx.fillRect(70, height - 100, 40, 100);
    
    ctx.fillStyle = '#e53e3e';
    ctx.fillRect(120, height - 40, 40, 40);
    
    ctx.fillStyle = '#d69e2e';
    ctx.fillRect(170, height - 80, 40, 80);
    
    // Add labels
    ctx.fillStyle = '#4a5568';
    ctx.font = '12px Roboto';
    ctx.textAlign = 'center';
    ctx.fillText('Q1', 40, height - 5);
    ctx.fillText('Q2', 90, height - 5);
    ctx.fillText('Q3', 140, height - 5);
    ctx.fillText('Q4', 190, height - 5);
}

// 7. Workflow Functions

function startWorkflow() {
    if (isWorkflowRunning) return;
    
    isWorkflowRunning = true;
    currentWorkflowStep = 1;
    
    const timelineSteps = document.querySelectorAll('.timeline-step');
    
    // Reset all steps
    timelineSteps.forEach(step => {
        step.classList.remove('active', 'completed');
    });
    
    // Start workflow progression
    function progressWorkflow() {
        if (currentWorkflowStep > 6) {
            isWorkflowRunning = false;
            return;
        }
        
        const currentStep = document.querySelector(`[data-step="${currentWorkflowStep}"]`);
        const previousStep = document.querySelector(`[data-step="${currentWorkflowStep - 1}"]`);
        
        if (previousStep) {
            previousStep.classList.remove('active');
            previousStep.classList.add('completed');
        }
        
        currentStep.classList.add('active');
        
        // Simulate step processing
        setTimeout(() => {
            currentWorkflowStep++;
            progressWorkflow();
        }, 2000);
    }
    
    progressWorkflow();
}

function resetWorkflow() {
    isWorkflowRunning = false;
    currentWorkflowStep = 1;
    
    const timelineSteps = document.querySelectorAll('.timeline-step');
    timelineSteps.forEach(step => {
        step.classList.remove('active', 'completed');
    });
    
    // Activate first step
    const firstStep = document.querySelector('[data-step="1"]');
    if (firstStep) {
        firstStep.classList.add('active');
    }
}

// Helper Functions

function initializeCharts() {
    updateTorqueChart();
    updateFailureRate();
    updateHeatmap();
    updateROIChart();
}

function updateTorqueChart() {
    const canvas = document.getElementById('torqueChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Draw simple line chart
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    const data = [45, 52, 48, 55, 50, 53, 47, 51];
    const stepX = width / (data.length - 1);
    const maxValue = Math.max(...data);
    
    data.forEach((value, index) => {
        const x = index * stepX;
        const y = height - (value / maxValue) * height;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    
    ctx.stroke();
}

function updateFailureRate() {
    const rateValue = document.querySelector('.rate-value');
    if (rateValue) {
        const newRate = (Math.random() * 5).toFixed(1);
        rateValue.textContent = newRate + '%';
        
        // Update circle color based on rate
        const rateCircle = document.querySelector('.rate-circle');
        if (newRate < 2) {
            rateCircle.style.background = 'conic-gradient(#38a169 0deg ' + (newRate * 7.2) + 'deg, #e2e8f0 ' + (newRate * 7.2) + 'deg 360deg)';
            rateValue.style.color = '#38a169';
        } else if (newRate < 4) {
            rateCircle.style.background = 'conic-gradient(#d69e2e 0deg ' + (newRate * 7.2) + 'deg, #e2e8f0 ' + (newRate * 7.2) + 'deg 360deg)';
            rateValue.style.color = '#d69e2e';
        } else {
            rateCircle.style.background = 'conic-gradient(#e53e3e 0deg ' + (newRate * 7.2) + 'deg, #e2e8f0 ' + (newRate * 7.2) + 'deg 360deg)';
            rateValue.style.color = '#e53e3e';
        }
    }
}

function updateHeatmap() {
    const heatmapCells = document.querySelectorAll('.heatmap-cell');
    const times = ['38s', '41s', '45s', '42s', '39s', '43s', '40s', '44s'];
    
    heatmapCells.forEach((cell, index) => {
        const time = times[Math.floor(Math.random() * times.length)];
        cell.textContent = time;
        
        const seconds = parseInt(time);
        if (seconds < 40) {
            cell.className = 'heatmap-cell low';
        } else if (seconds < 43) {
            cell.className = 'heatmap-cell medium';
        } else {
            cell.className = 'heatmap-cell high';
        }
    });
}

function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #667eea;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        z-index: 1000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Mock functions for access control
function hasBarcodeScanned() {
    return Math.random() > 0.3;
}

function hasOperatorAuth() {
    return Math.random() > 0.2;
}

function hasQualityCheck() {
    return Math.random() > 0.1;
}

// Auto-update functions for real-time simulation
setInterval(() => {
    if (Math.random() > 0.7) {
        updateToolStatus();
    }
}, 10000);

setInterval(() => {
    if (Math.random() > 0.8) {
        updateAnalytics();
    }
}, 15000);

setInterval(() => {
    if (Math.random() > 0.9) {
        triggerAlert();
    }
}, 20000);

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case '1':
                e.preventDefault();
                document.querySelector('[href="#overview"]').click();
                break;
            case '2':
                e.preventDefault();
                document.querySelector('[href="#integration"]').click();
                break;
            case '3':
                e.preventDefault();
                document.querySelector('[href="#customization"]').click();
                break;
            case '4':
                e.preventDefault();
                document.querySelector('[href="#integration-systems"]').click();
                break;
            case '5':
                e.preventDefault();
                document.querySelector('[href="#analytics"]').click();
                break;
            case '6':
                e.preventDefault();
                document.querySelector('[href="#roi"]').click();
                break;
            case '7':
                e.preventDefault();
                document.querySelector('[href="#workflow"]').click();
                break;
        }
    }
});

// Add loading states to buttons
document.querySelectorAll('button').forEach(button => {
    button.addEventListener('click', function() {
        if (!this.disabled) {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        }
    });
});

// Initialize the demo
console.log('PF6000 Open Protocol Animation Demo loaded successfully!');
console.log('Use Ctrl/Cmd + 1-7 for quick navigation between sections.'); 
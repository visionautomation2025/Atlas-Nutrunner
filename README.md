# Automated Barcode & Tightening System Demo

An interactive HTML, CSS, and JavaScript demo simulating an automated barcode & tightening system powered by Atlas Copco Power Focus Controller. This demo provides a visual walkthrough of the complete workflow with engaging animations, sound effects, and real-time feedback.

## Features

### 🎯 Interactive Workflow
- **6-Step Process**: Complete simulation of the automated tightening workflow
- **Real-time Feedback**: Live status updates and visual indicators
- **Progress Tracking**: Step-by-step progress bar and navigation

### 📊 Visual Elements
- **Barcode Scanner Animation**: Simulated scanning with visual feedback
- **Component Placement**: Interactive component placement with sensor status
- **Cylinder Animation**: Animated pneumatic cylinder movement
- **Torque vs. Angle Chart**: Real-time Chart.js visualization
- **Pass/Fail Banners**: Clear visual feedback for results

### 🔊 Audio Feedback
- **Scan Sounds**: Audio feedback for barcode scanning
- **Pass/Fail Sounds**: Distinct sounds for successful/failed operations
- **Error Alerts**: Audio cues for invalid operations

### 🎨 Modern UI/UX
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Color-coded Status**: Green (success), Red (error), Yellow (waiting)
- **Smooth Animations**: CSS transitions and keyframe animations
- **Professional Styling**: Clean, modern interface with gradients and shadows

## Workflow Steps

### Step 1: Scan Barcode
- Simulated barcode scanner with animated scanning beam
- Random barcode generation for demo purposes
- Success/error feedback with audio cues
- Invalid scan simulation available

### Step 2: Place Component
- Interactive component placement area
- Part sensor status monitoring
- Visual feedback when component is detected

### Step 3: Press Cycle Start
- Large, prominent cycle start button
- Animated cylinder movement (forward)
- Reed switch simulation
- Auto-advance to tightening process

### Step 4: Tightening Process
- **Real-time Torque vs. Angle Chart**: Live-updating Chart.js visualization
- **Live Metrics**: Current torque and angle display
- **Target Values**: Display of target specifications
- **Random Pass/Fail**: 70% pass rate for demo variety
- **Audio Feedback**: Success/failure sounds

### Step 5: Pass Sequence
- **Green PASS Banner**: Large success indicator
- **Cylinder Retraction**: Animated reverse movement
- **Component Removal**: Prompt for next action
- **Summary Report**: Complete cycle data

### Step 6: Fail Sequence
- **Red FAIL Banner**: Large failure indicator
- **Rejection Bin**: Component disposal simulation
- **Password Protection**: Tool reactivation (demo password: 1234)
- **Summary Report**: Complete cycle data

## Technical Features

### 📱 Responsive Design
- Mobile-first approach
- Touch/swipe navigation support
- Adaptive layouts for different screen sizes
- Optimized for tablets and mobile devices

### ⌨️ Keyboard Navigation
- **Arrow Keys**: Navigate between steps
- **Enter Key**: Trigger current step action
- **Tab Navigation**: Full keyboard accessibility

### 📊 Chart.js Integration
- Real-time torque vs. angle plotting
- Dual Y-axis for different units
- Smooth animations and interactions
- Performance optimized (50-point rolling window)

### 🎵 Audio System
- Base64 encoded audio files (no external dependencies)
- Fallback handling for browsers with audio restrictions
- Volume control and error handling

## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- No additional software installation required

### Installation
1. Download all files to a local directory:
   - `index.html`
   - `styles.css`
   - `script.js`
   - `README.md`

2. Open `index.html` in your web browser

### Usage
1. **Start Demo**: Click the "Start Demo" button on the intro screen
2. **Navigate**: Use arrow buttons or keyboard arrows to move between steps
3. **Interact**: Click action buttons to simulate real operations
4. **Observe**: Watch real-time animations and status updates
5. **Complete**: Follow the workflow to see the complete cycle

### Demo Controls
- **Scan Barcode**: Click "Scan Barcode" or "Simulate Invalid Scan"
- **Place Component**: Click "Place Component" button
- **Cycle Start**: Click the large "CYCLE START" button
- **Remove Component**: Click "Remove Component" (pass sequence)
- **Move to Rejection**: Click "Move to Rejection Bin" (fail sequence)
- **Password**: Enter "1234" to reactivate tool (fail sequence)

## Customization

### Colors and Styling
- Modify CSS variables in `styles.css` for brand colors
- Adjust gradients and shadows for different visual themes
- Customize animations and transitions

### Workflow Logic
- Edit `script.js` to modify step behavior
- Adjust timing and animations
- Change pass/fail probability rates

### Audio
- Replace base64 audio with external sound files
- Add additional sound effects
- Implement volume controls

## Browser Compatibility

- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 12+
- ✅ Edge 79+
- ⚠️ Internet Explorer (not supported)

## Performance Notes

- Chart.js updates are optimized for smooth performance
- Audio files are base64 encoded to avoid external dependencies
- CSS animations use hardware acceleration where possible
- Touch events are debounced for mobile performance

## Demo Password

For the fail sequence password prompt, use: **1234**

## License

This demo is provided as-is for educational and demonstration purposes. Feel free to modify and adapt for your specific needs.

## Support

For questions or issues with the demo, please refer to the code comments or create an issue in the repository.

---

**Note**: This is a simulation demo and does not connect to actual Atlas Copco Power Focus Controller hardware. It is designed for training, demonstration, and educational purposes only. 
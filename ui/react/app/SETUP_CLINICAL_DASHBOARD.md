# Clinical Dashboard Setup Instructions

## Current Status

The Clinical Dashboard has been created with all components, but some dependencies need to be installed.

## Issue: npm is in offline mode

Your npm is currently configured with `offline = true`, which prevents downloading packages.

## Solution: Install Dependencies

### Step 1: Enable npm online mode

Run this command to allow npm to download packages:

```bash
npm config set offline false
```

### Step 2: Install required packages

Navigate to the app directory and install dependencies:

```bash
cd ui/react/app
npm install recharts lucide-react tailwindcss postcss autoprefixer
```

### Step 3: Enable Tailwind CSS

After installing Tailwind, uncomment the Tailwind directives in `src/styles.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

And update `postcss.config.js` to:

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

## Temporary Workaround

The app should now run with fallback CSS classes. The dashboard will work, but for full Tailwind styling, follow the steps above.

## Components Created

✅ PatientHeader - Patient status and MVC display
✅ RealTimeBiofeedback - RMS envelope with target zone
✅ FrequencyDomainChart - Welch PSD with median frequency
✅ FatigueTrend - Sparkline for f_med trend
✅ ActionSidebar - Quick action buttons
✅ ClinicalDashboard - Main dashboard page

## Access the Dashboard

Once the app is running, navigate to: `/clinical`

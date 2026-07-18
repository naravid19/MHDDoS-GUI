# Timeframe Dropdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a sleek, minimalist dropdown for the 8 timeframe options across the UI.

**Architecture:** We will create a shared dropdown UI element using Tailwind CSS, and manage its state with a small inline JS script in `index.html` and `index-new.html` (or via `script.js` where applicable). The dropdown relies on absolute positioning relative to a parent container.

**Tech Stack:** HTML, Tailwind CSS, Vanilla JS

## Global Constraints

No new dependencies. Minimalist UI (Option C).

---

### Task 1: Add Global JS Logic for Dropdown

**Files:**
- Modify: `web/legacy/script.js`

**Interfaces:**
- Consumes: User click events.
- Produces: UI toggle logic for dropdown and timeframe updates.

- [ ] **Step 1: Write Dropdown Logic in script.js**

Add the following functions to manage the dropdown state and select timeframe:

```javascript
// Dropdown toggle logic
function toggleTimeframeDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

// Update UI and call setTimeframe
function selectTimeframeDropdown(value, labelId, dropdownId) {
    const label = document.getElementById(labelId);
    if (label) {
        label.innerText = value;
    }
    toggleTimeframeDropdown(dropdownId);
    
    // Call existing function
    if (typeof setTimeframe === 'function') {
        setTimeframe(value);
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    const dropdowns = document.querySelectorAll('.tf-dropdown-menu');
    const triggers = document.querySelectorAll('.tf-dropdown-trigger');
    
    let isClickInside = false;
    
    triggers.forEach(trigger => {
        if (trigger.contains(event.target)) isClickInside = true;
    });
    dropdowns.forEach(dropdown => {
        if (dropdown.contains(event.target)) isClickInside = true;
    });

    if (!isClickInside) {
        dropdowns.forEach(dropdown => {
            dropdown.classList.add('hidden');
        });
    }
});
```

- [ ] **Step 2: Commit**

```bash
git add web/legacy/script.js
git commit -m "feat(ui): add timeframe dropdown logic to script.js"
```

---

### Task 2: Update index.html Dropdown UI

**Files:**
- Modify: `web/index.html`

**Interfaces:**
- Consumes: The JS functions `toggleTimeframeDropdown` and `selectTimeframeDropdown`.

- [ ] **Step 1: Replace Timeframe UI in index.html**

Replace the current scrollable button row with the new dropdown UI:

```html
                            <div class="flex items-center gap-4">
                                Network Velocity Tracking
                                <div class="relative">
                                    <button class="tf-dropdown-trigger bg-gray-800/50 hover:bg-gray-700/80 text-gray-300 px-3 py-1.5 rounded-lg border border-gray-700/50 flex items-center gap-2 text-xs font-mono transition-all" onclick="toggleTimeframeDropdown('tf-dropdown-index')">
                                        <span id="tf-label-index">1H</span>
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
                                            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                                        </svg>
                                    </button>
                                    <div id="tf-dropdown-index" class="tf-dropdown-menu hidden absolute right-0 mt-2 w-24 bg-gray-900/95 border border-gray-800 rounded-lg shadow-2xl backdrop-blur-xl z-50 overflow-hidden flex flex-col py-1">
                                        <button class="text-left px-4 py-2 text-xs font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('1M', 'tf-label-index', 'tf-dropdown-index')">1M</button>
                                        <button class="text-left px-4 py-2 text-xs font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('5M', 'tf-label-index', 'tf-dropdown-index')">5M</button>
                                        <button class="text-left px-4 py-2 text-xs font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('30M', 'tf-label-index', 'tf-dropdown-index')">30M</button>
                                        <button class="text-left px-4 py-2 text-xs font-mono text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('1H', 'tf-label-index', 'tf-dropdown-index')">1H</button>
                                        <button class="text-left px-4 py-2 text-xs font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('3H', 'tf-label-index', 'tf-dropdown-index')">3H</button>
                                        <button class="text-left px-4 py-2 text-xs font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('6H', 'tf-label-index', 'tf-dropdown-index')">6H</button>
                                        <button class="text-left px-4 py-2 text-xs font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('12H', 'tf-label-index', 'tf-dropdown-index')">12H</button>
                                        <button class="text-left px-4 py-2 text-xs font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('1D', 'tf-label-index', 'tf-dropdown-index')">24H</button>
                                    </div>
                                </div>
                            </div>
```

- [ ] **Step 2: Commit**

```bash
git add web/index.html
git commit -m "feat(ui): implement timeframe dropdown in index.html"
```

---

### Task 3: Update index-new.html Dropdown UI

**Files:**
- Modify: `web/index-new.html`

**Interfaces:**
- Consumes: The JS functions `toggleTimeframeDropdown` and `selectTimeframeDropdown`.

- [ ] **Step 1: Replace Timeframe UI in index-new.html**

Replace the current scrollable button row with the new dropdown UI. Include the inline script tags at the bottom to ensure logic handles it since index-new might not load `script.js` directly. Or simply add the same dropdown and assume the JS is loaded or will be added. (We add the script inline at the end of the `<body>` just in case).

For the HTML element:

```html
<div class="flex space-x-2">
<span class="text-[10px] font-['JetBrains_Mono'] text-primary flex items-center"><span class="w-2 h-2 rounded-full bg-primary mr-1"></span> PPS</span>
<span class="text-[10px] font-['JetBrains_Mono'] text-secondary flex items-center"><span class="w-2 h-2 rounded-full bg-secondary mr-1"></span> Mbps</span>
<div class="relative ml-4">
    <button class="tf-dropdown-trigger bg-gray-800/50 hover:bg-gray-700/80 text-gray-300 px-3 py-1 rounded-lg border border-gray-700/50 flex items-center gap-2 text-[10px] font-mono transition-all" onclick="toggleTimeframeDropdown('tf-dropdown-new')">
        <span id="tf-label-new">1H</span>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
    </button>
    <div id="tf-dropdown-new" class="tf-dropdown-menu hidden absolute right-0 mt-2 w-24 bg-gray-900/95 border border-gray-800 rounded-lg shadow-2xl backdrop-blur-xl z-50 overflow-hidden flex flex-col py-1">
        <button class="text-left px-4 py-2 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('1M', 'tf-label-new', 'tf-dropdown-new')">1M</button>
        <button class="text-left px-4 py-2 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('5M', 'tf-label-new', 'tf-dropdown-new')">5M</button>
        <button class="text-left px-4 py-2 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('30M', 'tf-label-new', 'tf-dropdown-new')">30M</button>
        <button class="text-left px-4 py-2 text-[10px] font-mono text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('1H', 'tf-label-new', 'tf-dropdown-new')">1H</button>
        <button class="text-left px-4 py-2 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('3H', 'tf-label-new', 'tf-dropdown-new')">3H</button>
        <button class="text-left px-4 py-2 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('6H', 'tf-label-new', 'tf-dropdown-new')">6H</button>
        <button class="text-left px-4 py-2 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('12H', 'tf-label-new', 'tf-dropdown-new')">12H</button>
        <button class="text-left px-4 py-2 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors" onclick="selectTimeframeDropdown('1D', 'tf-label-new', 'tf-dropdown-new')">24H</button>
    </div>
</div>
```

At the bottom of `index-new.html`, before `</body>`:

```html
<script>
// Dropdown toggle logic
function toggleTimeframeDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

// Update UI and call setTimeframe
function selectTimeframeDropdown(value, labelId, dropdownId) {
    const label = document.getElementById(labelId);
    if (label) {
        label.innerText = value === '1D' ? '24H' : value;
    }
    toggleTimeframeDropdown(dropdownId);
    
    // Call existing function
    if (typeof setTimeframe === 'function') {
        setTimeframe(value);
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    const dropdowns = document.querySelectorAll('.tf-dropdown-menu');
    const triggers = document.querySelectorAll('.tf-dropdown-trigger');
    
    let isClickInside = false;
    
    triggers.forEach(trigger => {
        if (trigger.contains(event.target)) isClickInside = true;
    });
    dropdowns.forEach(dropdown => {
        if (dropdown.contains(event.target)) isClickInside = true;
    });

    if (!isClickInside) {
        dropdowns.forEach(dropdown => {
            dropdown.classList.add('hidden');
        });
    }
});
</script>
```

- [ ] **Step 2: Commit**

```bash
git add web/index-new.html
git commit -m "feat(ui): implement timeframe dropdown in index-new.html"
```

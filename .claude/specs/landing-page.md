# DispatchIQ — Landing Page & UI Redesign Spec

## 1. What Is This?
A professional public-facing landing page for DispatchIQ and a UI 
polish of all internal pages. Goal: make the app look like a ₹1 lakh 
SaaS product, not a college project.

## 2. What Changes
- NEW: Public landing page at "/" for non-logged-in users
- UPDATED: Internal pages get better styling, icons, animations
- UPDATED: Login page matches new branding
- ROUTE CHANGE: Dashboard moves from "/" to "/dashboard"
- NO backend logic changes. Only templates and one route change.

## 3. CDN Libraries (All Free)
- Tailwind CSS: https://cdn.tailwindcss.com (already using)
- AOS.js: https://unpkg.com/aos@2.3.4/dist/aos.css + aos.js
- Lucide Icons: https://unpkg.com/lucide@latest
- Google Font Inter: https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900

## 4. Brand Guidelines
- Primary color: Amber/Gold (#F59E0B, Tailwind amber-500)
- Background: Gray-950 (#030712) to Gray-900 (#111827)
- Card backgrounds: Gray-900/50 with backdrop-blur
- Text: White for headings, Gray-400 for body
- Font: Inter (all weights)
- Border radius: rounded-2xl for cards, rounded-xl for buttons/inputs
- Hover effects on everything interactive
- Dark theme ONLY — no light mode

## 5. Landing Page Sections (templates/landing.html)
This is a STANDALONE template. Does NOT extend base.html.
Only visible to NON-logged-in users. Logged-in users redirect to /dashboard.

### Section 1: Hero (Full viewport height)
- Animated gradient orbs in background (pure CSS @keyframes)
- Badge: "🚛 Built for Indian Logistics"
- Heading: "Dispatch Smarter." + "Deliver Faster." (amber)
- Subtitle explaining the product
- CTA buttons: "Get Started →" (amber) + "Watch Demo ▶" (outline)
- Mini dashboard mockup below (pure HTML/CSS, not an image)
- AOS: fade-up animations with staggered delays

### Section 2: Features (6 cards in 3x2 grid)
- Trip Management (truck icon)
- Auto LR & Invoice (file-text icon)
- WhatsApp Alerts (message-circle icon)
- AI-Powered (bot icon)
- Live GPS Tracking (map-pin icon)
- Payment Tracking (wallet icon)
- Cards: bg-gray-900/50, border-gray-800, hover:border-amber-500/50
- AOS: fade-up staggered

### Section 3: How It Works (3 steps)
- Install → Configure → Dispatch
- Number circles in amber, connecting line
- AOS: fade-right staggered

### Section 4: Stats
- "500+" Trips Managed | "₹50L+" Revenue Tracked | "100%" Automated
- AOS: zoom-in

### Section 5: Comparison Table
- Manual Process vs DispatchIQ (5 rows)
- Green checkmarks for DispatchIQ column

### Section 6: CTA
- Amber gradient card
- "Ready to Modernize Your Transport Business?"
- "Sign In →" button

### Section 7: Footer
- Logo + copyright + "Built with ❤️ in India"

## 6. Internal UI Updates

### base.html
- Add Inter font + Lucide icons CDN
- Glass effect navbar (bg-gray-900/80 backdrop-blur-xl)
- Active page amber underline
- Smooth user dropdown animation

### dashboard.html
- Stat cards: gradient borders, hover:scale-105, Lucide icons
- Better table hover effects
- Better spacing

### All list pages (trips, vehicles, drivers, clients, payments)
- Table row hover effects
- Consistent status badge styling (rounded-full + dot)
- Empty state messages when no data

### All form pages
- Larger inputs, rounded-xl, focus:ring-2 ring-amber-500
- Full width submit buttons on mobile
- Amber gradient buttons

### auth/login.html
- Match landing page aesthetic
- Animated gradient orbs background
- Glassmorphism card

## 7. Route Change
- GET "/" → if logged in → redirect to /dashboard
         → if not logged in → show landing.html
- GET "/dashboard" → current dashboard (requires login)

## 8. Constraints
- ALL styling via Tailwind classes only — no separate CSS files
- No backend logic changes — only templates + one route
- Mobile responsive (test mentally at 375px)
- AOS.init({duration: 800, once: true})
- lucide.createIcons() after page load
- Landing page must load fast — no heavy images
- Don't break ANY existing functionality
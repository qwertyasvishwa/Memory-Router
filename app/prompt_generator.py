"""
Automatic Prompt Generator for AI Tools Creation Application

Generates step-by-step implementation prompts based on requirements gap analysis.
Each prompt is designed to be executed sequentially by VS Code Copilot.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import json
from datetime import datetime
from pathlib import Path


class PromptPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PromptCategory(str, Enum):
    SETUP = "setup"
    FRONTEND = "frontend"
    BACKEND = "backend"
    AI_INTEGRATION = "ai_integration"
    UI_UX = "ui_ux"
    TESTING = "testing"


@dataclass
class ImplementationPrompt:
    """Single implementation step with detailed prompt for Copilot"""
    id: int
    title: str
    category: PromptCategory
    priority: PromptPriority
    prompt: str
    dependencies: List[int]  # IDs of prompts that must complete first
    estimated_time: str
    acceptance_criteria: List[str]
    files_to_create: List[str]
    files_to_modify: List[str]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "priority": self.priority.value,
            "prompt": self.prompt,
            "dependencies": self.dependencies,
            "estimated_time": self.estimated_time,
            "acceptance_criteria": self.acceptance_criteria,
            "files_to_create": self.files_to_create,
            "files_to_modify": self.files_to_modify,
        }


class PromptGenerator:
    """Generates implementation prompts for transforming Memory Router"""

    def __init__(self):
        self.prompts: List[ImplementationPrompt] = []
        self._generate_all_prompts()

    def _generate_all_prompts(self):
        """Generate all implementation prompts in execution order"""

        # Phase 1: Foundation & Setup
        self.prompts.append(ImplementationPrompt(
            id=1,
            title="Install React and frontend dependencies",
            category=PromptCategory.SETUP,
            priority=PromptPriority.CRITICAL,
            prompt="""Install React frontend dependencies for the AI Tools Creation Application.

Requirements:
- Create a new React app using Vite in the 'frontend' directory
- Install required packages: react, react-dom, react-router-dom, axios, tailwindcss
- Set up Tailwind CSS for premium minimal design system
- Configure proxy to FastAPI backend (port 8000)
- Create basic folder structure: src/components, src/pages, src/services, src/styles
- Add TypeScript support for better type safety

Commands to run:
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

Create package.json with proxy configuration to http://localhost:8000""",
            dependencies=[],
            estimated_time="15 minutes",
            acceptance_criteria=[
                "frontend/ directory created with Vite + React + TypeScript",
                "Tailwind CSS configured",
                "npm run dev starts development server",
                "Proxy to backend configured"
            ],
            files_to_create=[
                "frontend/package.json",
                "frontend/vite.config.ts",
                "frontend/tailwind.config.js",
                "frontend/src/App.tsx",
                "frontend/src/main.tsx"
            ],
            files_to_modify=[]
        ))

        self.prompts.append(ImplementationPrompt(
            id=2,
            title="Set up Azure OpenAI integration in backend",
            category=PromptCategory.AI_INTEGRATION,
            priority=PromptPriority.CRITICAL,
            prompt="""Add Azure OpenAI integration to the FastAPI backend for AI-powered content generation.

Requirements:
- Install openai Python package (pip install openai)
- Create app/ai_client.py with AzureOpenAIClient class
- Add environment variables: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT
- Implement methods: generate_social_post(), generate_prd(), generate_image_prompt()
- Add retry logic and error handling
- Include token usage tracking
- Add streaming support for real-time responses

The client should support:
1. Content generation (GPT-4)
2. Image generation (DALL-E 3)
3. Prompt caching for efficiency
4. Rate limiting and quota management

Update app/config.py to include Azure OpenAI settings.
Add requirements.txt entry: openai>=1.0.0""",
            dependencies=[],
            estimated_time="30 minutes",
            acceptance_criteria=[
                "app/ai_client.py created with AzureOpenAIClient",
                "Environment variables configured",
                "Test endpoint /api/ai/test returns successful response",
                "Error handling and retry logic implemented"
            ],
            files_to_create=[
                "app/ai_client.py"
            ],
            files_to_modify=[
                "app/config.py",
                "requirements.txt"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=3,
            title="Create modular React component architecture",
            category=PromptCategory.FRONTEND,
            priority=PromptPriority.HIGH,
            prompt="""Build the modular component architecture for the AI Tools Creation dashboard.

Create these React components with TypeScript:

1. **Layout Components:**
   - src/components/Layout/DashboardLayout.tsx - Main layout with sidebar
   - src/components/Layout/Header.tsx - Top navigation bar
   - src/components/Layout/Sidebar.tsx - Modular tool navigation

2. **Dashboard Components:**
   - src/components/Dashboard/ProjectCard.tsx - Project display card
   - src/components/Dashboard/ProjectGrid.tsx - Grid layout for projects
   - src/components/Dashboard/ModuleGrid.tsx - Dynamic module loader

3. **Tool Module Components:**
   - src/components/Modules/ContentGenerator.tsx - AI content generation
   - src/components/Modules/DesignPreview.tsx - Visual preview panel
   - src/components/Modules/ProjectManager.tsx - Project CRUD operations

4. **Shared Components:**
   - src/components/UI/Card.tsx - Reusable card component
   - src/components/UI/Button.tsx - Premium button styles
   - src/components/UI/Input.tsx - Form input components

Apply premium minimal design:
- Clean layouts with generous whitespace
- Neutral colors: #FFFFFF, #333333, accent #0366d6
- Modern typography: system-ui font stack
- Subtle shadows and hover states
- Responsive design (desktop + tablet)

Each component should be independently importable and follow composition patterns.""",
            dependencies=[1],
            estimated_time="90 minutes",
            acceptance_criteria=[
                "All components created with TypeScript interfaces",
                "Components follow premium minimal design principles",
                "Each component is independently usable",
                "Storybook or component preview available"
            ],
            files_to_create=[
                "frontend/src/components/Layout/DashboardLayout.tsx",
                "frontend/src/components/Layout/Header.tsx",
                "frontend/src/components/Layout/Sidebar.tsx",
                "frontend/src/components/Dashboard/ProjectCard.tsx",
                "frontend/src/components/Dashboard/ProjectGrid.tsx",
                "frontend/src/components/Dashboard/ModuleGrid.tsx",
                "frontend/src/components/Modules/ContentGenerator.tsx",
                "frontend/src/components/Modules/DesignPreview.tsx",
                "frontend/src/components/Modules/ProjectManager.tsx",
                "frontend/src/components/UI/Card.tsx",
                "frontend/src/components/UI/Button.tsx",
                "frontend/src/components/UI/Input.tsx"
            ],
            files_to_modify=[]
        ))

        self.prompts.append(ImplementationPrompt(
            id=4,
            title="Implement template engine for brand consistency",
            category=PromptCategory.BACKEND,
            priority=PromptPriority.HIGH,
            prompt="""Create a template engine system for consistent branding across all generated content.

Build app/template_engine.py with:

1. **BrandIdentity class:**
   - Properties: logo_url, primary_color, secondary_color, font_family, accent_color
   - Load from project configuration
   - Support multiple brand profiles (e.g., Happy Eats, Vishwa OS)

2. **TemplateEngine class:**
   - render_social_post(content, brand, layout_type) - Returns HTML/image
   - render_prd(content, brand) - Returns formatted document
   - apply_brand_theme(template, brand) - Injects brand variables
   - generate_preview_html(content, brand) - For real-time preview

3. **Template Types:**
   - Social media posts (Instagram square, LinkedIn banner, Twitter card)
   - PRD documents (structured markdown with brand header)
   - Email templates
   - Presentation slides

4. **Storage:**
   - Store brand configs in app/brands/ directory as JSON
   - Store HTML templates in app/templates/content/ directory
   - Cache rendered templates for performance

Integration:
- Add FastAPI endpoint: POST /api/templates/render
- Support Jinja2 template syntax with brand variables
- Return both HTML and downloadable image formats (JPG, PNG)

Install: Pillow for image generation, jinja2 (already installed)""",
            dependencies=[],
            estimated_time="60 minutes",
            acceptance_criteria=[
                "app/template_engine.py created with BrandIdentity and TemplateEngine",
                "Sample brand configs created (Happy Eats, default)",
                "Templates render with brand colors and logos",
                "API endpoint /api/templates/render functional"
            ],
            files_to_create=[
                "app/template_engine.py",
                "app/brands/happy_eats.json",
                "app/brands/default.json",
                "app/templates/content/social_post.html",
                "app/templates/content/prd.html"
            ],
            files_to_modify=[
                "requirements.txt",
                "app/main.py"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=5,
            title="Build AI content generation API endpoints",
            category=PromptCategory.AI_INTEGRATION,
            priority=PromptPriority.HIGH,
            prompt="""Create FastAPI endpoints for AI-powered content generation.

Add to app/main.py:

1. **POST /api/ai/generate/social-post**
   - Input: { project_id, theme, platform, brand_guidelines }
   - Uses Azure OpenAI to generate post series (3-5 posts)
   - Applies brand template
   - Returns: { posts: [], preview_urls: [] }

2. **POST /api/ai/generate/prd**
   - Input: { project_id, feature_description, requirements }
   - Generates structured PRD document
   - Includes: overview, user stories, acceptance criteria, technical specs
   - Returns formatted markdown + PDF download link

3. **POST /api/ai/generate/image**
   - Input: { prompt, style, brand_id }
   - Uses DALL-E 3 for image generation
   - Applies brand colors/style
   - Returns image URL and downloadable formats

4. **GET /api/ai/suggestions**
   - Input: project_id
   - Analyzes project documents
   - Suggests next content to create
   - Returns: { suggestions: [{ type, title, reason }] }

Error handling:
- Rate limit protection (429 errors)
- Token quota management
- Graceful degradation if AI unavailable
- Progress tracking for long-running generations

Add streaming support for real-time generation feedback.
Log all AI requests to ledger for audit trail.""",
            dependencies=[2, 4],
            estimated_time="75 minutes",
            acceptance_criteria=[
                "All 4 endpoints implemented and tested",
                "AI client integration working",
                "Template engine applied to outputs",
                "Error handling covers edge cases",
                "Streaming responses functional"
            ],
            files_to_create=[],
            files_to_modify=[
                "app/main.py",
                "app/ai_client.py",
                "app/schemas.py"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=6,
            title="Create project management system with folder structure",
            category=PromptCategory.BACKEND,
            priority=PromptPriority.HIGH,
            prompt="""Build comprehensive project management system with SharePoint folder organization.

Create app/project_manager.py with:

1. **Project class:**
   - Properties: id, name, description, brand_id, created_at, folder_path
   - Methods: create_folder_structure(), list_inputs(), list_outputs()

2. **ProjectManager service:**
   - create_project(name, description, brand_id) - Creates SharePoint folder structure
   - get_project(project_id) - Retrieves project with all metadata
   - list_projects() - Returns all projects with stats
   - delete_project(project_id) - Archives project
   - upload_input_document(project_id, file) - Stores source materials
   - get_outputs(project_id, type) - Lists generated content

3. **SharePoint Folder Structure:**
   ```
   /Projects/{project_name}/
     /inputs/              # Brand guidelines, source docs
     /outputs/
       /social-posts/      # Generated social media content
       /prds/              # Product requirement documents
       /images/            # Generated visuals
     /config/
       brand.json          # Project-specific brand config
     metadata.json         # Project metadata
   ```

4. **API Endpoints:**
   - POST /api/projects - Create new project
   - GET /api/projects - List all projects
   - GET /api/projects/{id} - Get project details
   - PUT /api/projects/{id} - Update project
   - DELETE /api/projects/{id} - Archive project
   - POST /api/projects/{id}/inputs - Upload input files
   - GET /api/projects/{id}/outputs - List generated outputs

Integration with existing SharePoint client (app/sharepoint_client.py).
Add project caching for performance.""",
            dependencies=[],
            estimated_time="90 minutes",
            acceptance_criteria=[
                "app/project_manager.py created with Project and ProjectManager",
                "SharePoint folder structure auto-created on project creation",
                "All CRUD endpoints functional",
                "Project metadata persisted to SharePoint",
                "Input/output file management working"
            ],
            files_to_create=[
                "app/project_manager.py"
            ],
            files_to_modify=[
                "app/main.py",
                "app/schemas.py",
                "app/sharepoint_client.py"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=7,
            title="Build design preview and download system",
            category=PromptCategory.BACKEND,
            priority=PromptPriority.MEDIUM,
            prompt="""Create real-time design preview and export system for generated content.

Build app/preview_generator.py with:

1. **PreviewGenerator class:**
   - generate_html_preview(content, template, brand) - Renders HTML preview
   - generate_image(html, format='png', size=(1080, 1080)) - Converts HTML to image
   - generate_pdf(content) - Creates PDF from content
   - create_thumbnail(image, size=(300, 300)) - Generates preview thumbnails

2. **Image Export Formats:**
   - PNG (lossless, transparent background support)
   - JPG (compressed, social media ready)
   - WebP (modern format, smaller files)
   - PDF (documents and PRDs)

3. **Canvas/HTML Rendering:**
   - Use Playwright or similar for HTML to image conversion
   - Support custom dimensions per platform (Instagram: 1080x1080, Twitter: 1200x675)
   - Apply brand overlays (logos, watermarks)
   - High-resolution export (2x, 3x for retina displays)

4. **API Endpoints:**
   - POST /api/preview/generate - Generate preview from content
   - GET /api/preview/{preview_id} - Get preview HTML
   - GET /api/preview/{preview_id}/download - Download as image/PDF
   - POST /api/preview/batch - Generate multiple previews

5. **Caching Strategy:**
   - Cache generated images in SharePoint /outputs/ folders
   - Store preview URLs in project metadata
   - Invalidate cache on content update

Requirements:
- Install: pillow, playwright (or imgkit, wkhtmltoimage)
- Support background jobs for slow generation
- Progress tracking via websockets or polling

Return structure: { preview_url, download_urls: {png, jpg, pdf}, thumbnail_url }""",
            dependencies=[4],
            estimated_time="120 minutes",
            acceptance_criteria=[
                "HTML to image conversion working",
                "Multiple export formats supported (PNG, JPG, PDF)",
                "Download endpoints functional",
                "Preview thumbnails generated",
                "High-resolution exports available"
            ],
            files_to_create=[
                "app/preview_generator.py"
            ],
            files_to_modify=[
                "app/main.py",
                "requirements.txt"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=8,
            title="Connect React frontend to backend APIs",
            category=PromptCategory.FRONTEND,
            priority=PromptPriority.HIGH,
            prompt="""Create API service layer and connect React components to FastAPI backend.

Build frontend/src/services/:

1. **api.ts** - Axios configuration
   - Base URL: http://localhost:8000
   - Request/response interceptors
   - Error handling wrapper
   - Token management (if auth added later)

2. **projectService.ts:**
   - createProject(data)
   - getProjects()
   - getProject(id)
   - updateProject(id, data)
   - deleteProject(id)
   - uploadInput(projectId, file)
   - getOutputs(projectId)

3. **aiService.ts:**
   - generateSocialPost(data)
   - generatePRD(data)
   - generateImage(data)
   - getSuggestions(projectId)

4. **previewService.ts:**
   - generatePreview(content, template, brand)
   - downloadAsset(previewId, format)
   - getPreview(previewId)

5. **React Query Integration:**
   - Install @tanstack/react-query
   - Create hooks: useProjects(), useProject(id), useAIGenerate()
   - Implement caching and optimistic updates
   - Handle loading and error states

6. **State Management:**
   - Use Context API or Zustand for global state
   - Store: current project, active modules, user preferences
   - Persist state to localStorage

Update components to use API hooks:
- ProjectGrid uses useProjects()
- ContentGenerator uses useAIGenerate()
- DesignPreview uses usePreview()

Add loading spinners and error boundaries for better UX.""",
            dependencies=[3, 5, 6],
            estimated_time="90 minutes",
            acceptance_criteria=[
                "All API services created with TypeScript types",
                "React Query configured and working",
                "Components fetch and display data from backend",
                "Loading and error states handled gracefully",
                "Optimistic updates for better UX"
            ],
            files_to_create=[
                "frontend/src/services/api.ts",
                "frontend/src/services/projectService.ts",
                "frontend/src/services/aiService.ts",
                "frontend/src/services/previewService.ts",
                "frontend/src/hooks/useProjects.ts",
                "frontend/src/hooks/useAI.ts",
                "frontend/src/types/index.ts"
            ],
            files_to_modify=[
                "frontend/src/components/Dashboard/ProjectGrid.tsx",
                "frontend/src/components/Modules/ContentGenerator.tsx",
                "frontend/src/components/Modules/DesignPreview.tsx",
                "frontend/package.json"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=9,
            title="Implement premium design system with micro-interactions",
            category=PromptCategory.UI_UX,
            priority=PromptPriority.MEDIUM,
            prompt="""Apply premium minimal design principles with emotional design elements.

Create frontend/src/styles/design-system.ts:

1. **Design Tokens:**
   ```typescript
   export const colors = {
     white: '#FFFFFF',
     charcoal: '#333333',
     gray: { 50: '#F9FAFB', 100: '#F3F4F6', ... },
     accent: '#0366d6',
     success: '#10B981',
     error: '#EF4444',
   };

   export const typography = {
     fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
     fontSize: { xs: '12px', sm: '14px', base: '16px', lg: '18px', xl: '24px' },
     fontWeight: { normal: 400, medium: 500, semibold: 600, bold: 700 },
   };

   export const spacing = { xs: '4px', sm: '8px', md: '16px', lg: '24px', xl: '32px' };
   export const borderRadius = { sm: '4px', md: '8px', lg: '12px', full: '9999px' };
   export const shadows = {
     sm: '0 1px 3px rgba(0, 0, 0, 0.08)',
     md: '0 4px 6px rgba(0, 0, 0, 0.1)',
     lg: '0 10px 15px rgba(0, 0, 0, 0.15)',
   };
   ```

2. **Micro-Interactions:**
   - Hover states: scale(1.02), brightness(1.1)
   - Button press: scale(0.98)
   - Card hover: shadow elevation increase
   - Loading animations: smooth spinner, skeleton screens
   - Success animations: checkmark fade-in, confetti
   - Transition timing: cubic-bezier(0.4, 0.0, 0.2, 1)

3. **Component Enhancements:**
   - Button.tsx: Add ripple effect, loading state, icon support
   - Card.tsx: Hover lift animation, interactive states
   - Input.tsx: Focus glow, validation animations
   - Modal.tsx: Smooth backdrop fade, slide-in content

4. **Emotional Feedback:**
   - Success messages: "Your design is ready! 🎉"
   - Error messages: "Oops! Something went wrong. Let's try that again."
   - Empty states: Encouraging illustrations and helpful CTAs
   - Tooltips: Contextual help on hover

5. **Accessibility:**
   - ARIA labels on all interactive elements
   - Keyboard navigation support (Tab, Enter, Escape)
   - Focus visible indicators
   - Screen reader announcements for state changes

6. **Responsive Design:**
   - Breakpoints: mobile (< 640px), tablet (< 1024px), desktop (>= 1024px)
   - Fluid typography and spacing
   - Touch-friendly targets (min 44px x 44px)

Install framer-motion for advanced animations.
Create Storybook stories for all components.""",
            dependencies=[3],
            estimated_time="120 minutes",
            acceptance_criteria=[
                "Design system tokens created and exported",
                "All components use design tokens",
                "Micro-interactions implemented (hover, press, etc.)",
                "Accessibility requirements met (ARIA, keyboard nav)",
                "Responsive design working across devices",
                "Emotional feedback messages in place"
            ],
            files_to_create=[
                "frontend/src/styles/design-system.ts",
                "frontend/src/styles/animations.ts",
                "frontend/src/components/Feedback/SuccessMessage.tsx",
                "frontend/src/components/Feedback/ErrorMessage.tsx",
                "frontend/src/components/Feedback/EmptyState.tsx"
            ],
            files_to_modify=[
                "frontend/src/components/UI/Button.tsx",
                "frontend/src/components/UI/Card.tsx",
                "frontend/src/components/UI/Input.tsx",
                "frontend/tailwind.config.js",
                "frontend/package.json"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=10,
            title="Build content generation workflow with guided steps",
            category=PromptCategory.FRONTEND,
            priority=PromptPriority.MEDIUM,
            prompt="""Create guided multi-step workflow for AI content generation with cognitive clarity.

Build frontend/src/components/Workflows/ContentGenerationWizard.tsx:

1. **Wizard Steps:**
   - Step 1: Select Project
     * Display project cards
     * Option to create new project
     * Show project stats (inputs uploaded, outputs generated)

   - Step 2: Choose Content Type
     * Social media posts (Instagram, LinkedIn, Twitter)
     * PRD document
     * Marketing email
     * Custom template

   - Step 3: Provide Inputs
     * Upload brand guidelines (drag & drop)
     * Enter content theme/topic
     * Select tone (professional, casual, enthusiastic)
     * Target audience specification

   - Step 4: Configure Brand
     * Select brand profile or create new
     * Preview brand colors and typography
     * Upload logo (optional)

   - Step 5: Generate & Review
     * AI generation progress indicator
     * Real-time preview as content generates
     * Edit generated content
     * Regenerate individual items

   - Step 6: Download & Export
     * Preview all formats (PNG, JPG, PDF)
     * Bulk download option
     * Share to project outputs folder
     * Copy to clipboard

2. **Progress Tracking:**
   - Visual stepper component (1 → 2 → 3 → 4 → 5 → 6)
   - Save draft at each step
   - "Back" and "Next" navigation
   - Skip optional steps
   - Progress percentage (e.g., "Step 3 of 6 - 50% complete")

3. **Smart Defaults:**
   - Pre-fill from last generation
   - Suggest content types based on project
   - Auto-detect brand from uploaded guidelines
   - Remember user preferences

4. **Validation:**
   - Required fields clearly marked
   - Inline error messages
   - Prevent advancement with incomplete data
   - Helpful hints: "Tip: Upload at least one brand guideline for best results"

5. **Keyboard Shortcuts:**
   - Ctrl+Enter: Advance to next step
   - Ctrl+B: Go back
   - Ctrl+S: Save draft
   - Escape: Cancel and return to dashboard

Build supporting components:
- Stepper.tsx - Visual progress indicator
- DragDropZone.tsx - File upload area
- ProgressBar.tsx - Generation progress
- PreviewPanel.tsx - Real-time content preview

Use React Hook Form for form management and validation.""",
            dependencies=[3, 8],
            estimated_time="120 minutes",
            acceptance_criteria=[
                "6-step wizard functional with navigation",
                "All steps have proper validation",
                "Progress saved at each step",
                "Keyboard shortcuts working",
                "Smart defaults and suggestions implemented",
                "Responsive design for tablet/desktop"
            ],
            files_to_create=[
                "frontend/src/components/Workflows/ContentGenerationWizard.tsx",
                "frontend/src/components/Workflows/Stepper.tsx",
                "frontend/src/components/UI/DragDropZone.tsx",
                "frontend/src/components/UI/ProgressBar.tsx",
                "frontend/src/components/Preview/PreviewPanel.tsx"
            ],
            files_to_modify=[
                "frontend/src/components/Modules/ContentGenerator.tsx",
                "frontend/package.json"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=11,
            title="Add dynamic brand identity system per project",
            category=PromptCategory.FRONTEND,
            priority=PromptPriority.MEDIUM,
            prompt="""Implement dynamic brand theming system that adapts UI to each project's brand identity.

Create frontend/src/contexts/BrandContext.tsx:

1. **Brand Context:**
   ```typescript
   interface BrandIdentity {
     id: string;
     name: string;
     logo: string;
     colors: {
       primary: string;
       secondary: string;
       accent: string;
       background: string;
       text: string;
     };
     typography: {
       fontFamily: string;
       headingFont: string;
     };
     assets: {
       logoUrl: string;
       iconUrl: string;
       watermark: string;
     };
   }

   const BrandContext = createContext<{
     activeBrand: BrandIdentity | null;
     setActiveBrand: (brand: BrandIdentity) => void;
     brandProfiles: BrandIdentity[];
   }>();
   ```

2. **Brand Application:**
   - Apply brand colors to UI when project selected
   - Update CSS variables dynamically: `--brand-primary`, `--brand-accent`
   - Show brand logo in dashboard header
   - Inject brand fonts via Google Fonts or custom @font-face
   - Use brand colors in generated previews

3. **Sample Brand Profiles:**
   - **Happy Eats:**
     * Primary: #FF6B35 (warm orange)
     * Secondary: #F7931E (golden)
     * Accent: #C1403D (red)
     * Font: Poppins
     * Logo: Happy Eats icon

   - **Vishwa OS:**
     * Primary: #0066CC (blue)
     * Secondary: #5856D6 (purple)
     * Accent: #34C759 (green)
     * Font: Inter
     * Logo: Vishwa icon

   - **Default:**
     * Primary: #0366d6
     * Secondary: #6c757d
     * Font: System UI

4. **Brand Management UI:**
   - frontend/src/pages/BrandManagement.tsx
   - Create/edit brand profiles
   - Upload logos and assets
   - Color picker for brand colors
   - Font selection dropdown (Google Fonts integration)
   - Preview how brand looks across templates

5. **Template Variables:**
   - Replace hardcoded colors in templates with brand variables
   - Support brand logo injection in social posts
   - Apply brand fonts to generated content
   - Watermark support for images

6. **Persistence:**
   - Save brand profiles to backend (/api/brands)
   - Cache active brand in localStorage
   - Sync brand changes across tabs (BroadcastChannel API)

Update all UI components to use brand context colors instead of hardcoded values.""",
            dependencies=[3, 4, 8],
            estimated_time="90 minutes",
            acceptance_criteria=[
                "Brand context created and provides brand data",
                "UI dynamically applies brand colors when project selected",
                "Sample brand profiles (Happy Eats, Vishwa OS) created",
                "Brand management page functional",
                "Generated content uses brand identity",
                "Brand persistence working"
            ],
            files_to_create=[
                "frontend/src/contexts/BrandContext.tsx",
                "frontend/src/pages/BrandManagement.tsx",
                "frontend/src/components/Brand/BrandSelector.tsx",
                "frontend/src/components/Brand/ColorPicker.tsx",
                "frontend/src/hooks/useBrand.ts"
            ],
            files_to_modify=[
                "frontend/src/components/Layout/DashboardLayout.tsx",
                "frontend/src/styles/design-system.ts",
                "frontend/src/App.tsx"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=12,
            title="Create plugin system for extensible modules",
            category=PromptCategory.BACKEND,
            priority=PromptPriority.LOW,
            prompt="""Enhance the existing tool registry into a full plugin system for modular dashboard extensibility.

Extend app/tools_registry.py:

1. **Plugin Manifest Structure:**
   ```python
   class PluginManifest(BaseModel):
       id: str
       name: str
       version: str
       description: str
       author: str
       icon: str  # URL or emoji
       category: str  # "content", "design", "analytics", "integration"

       # UI integration
       component_path: Optional[str]  # React component for UI
       dashboard_card: bool  # Show in module grid
       sidebar_link: bool  # Add to sidebar navigation

       # Backend integration
       api_endpoints: List[str]  # Exposed API routes
       hooks: Dict[str, str]  # Event hooks (on_project_create, etc.)

       # Dependencies
       requires: List[str]  # Required plugins
       permissions: List[str]  # SharePoint, OpenAI, etc.
   ```

2. **Plugin Lifecycle:**
   - register(manifest) - Add plugin to registry
   - activate(plugin_id) - Enable plugin
   - deactivate(plugin_id) - Disable plugin
   - unregister(plugin_id) - Remove plugin
   - get_plugins(category) - List plugins by category

3. **Sample Plugins:**
   - **Social Media Scheduler:**
     * Schedules posts to Buffer/Hootsuite
     * API: POST /api/plugins/scheduler/schedule

   - **Analytics Dashboard:**
     * Tracks generation metrics
     * Component: AnalyticsDashboard.tsx

   - **Canva Integration:**
     * Exports to Canva for further editing
     * OAuth flow for authentication

4. **Plugin Discovery:**
   - POST /api/plugins/install - Install from URL or upload
   - GET /api/plugins/marketplace - List available plugins
   - GET /api/plugins/installed - List installed plugins
   - PUT /api/plugins/{id}/config - Configure plugin settings

5. **Security:**
   - Sandboxed execution for third-party plugins
   - Permission system (require user approval for SharePoint access)
   - Code signing for verified plugins
   - Rate limiting per plugin

6. **Frontend Plugin Loader:**
   - Dynamically load React components from plugins
   - Render plugin cards in ModuleGrid
   - Add plugin routes to React Router
   - Inject plugin sidebar items

Create sample plugin package:
- app/plugins/hello_plugin/ with manifest.json and main.py
- Show how plugins extend the dashboard

Update tools.html to show plugin management UI.""",
            dependencies=[],
            estimated_time="120 minutes",
            acceptance_criteria=[
                "Plugin manifest system created",
                "Plugin lifecycle methods implemented",
                "Sample plugin created and working",
                "Plugin discovery and installation functional",
                "Security permissions enforced",
                "Frontend can load and render plugin components"
            ],
            files_to_create=[
                "app/plugin_system.py",
                "app/plugins/hello_plugin/manifest.json",
                "app/plugins/hello_plugin/main.py",
                "frontend/src/components/Plugins/PluginLoader.tsx",
                "frontend/src/pages/PluginMarketplace.tsx"
            ],
            files_to_modify=[
                "app/tools_registry.py",
                "app/main.py",
                "frontend/src/components/Dashboard/ModuleGrid.tsx"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=13,
            title="Add comprehensive testing suite",
            category=PromptCategory.TESTING,
            priority=PromptPriority.MEDIUM,
            prompt="""Create comprehensive testing suite for backend and frontend.

Backend Tests (pytest):

1. **Unit Tests:**
   - tests/test_ai_client.py - Mock Azure OpenAI responses
   - tests/test_template_engine.py - Template rendering
   - tests/test_project_manager.py - CRUD operations
   - tests/test_preview_generator.py - Image generation

2. **Integration Tests:**
   - tests/test_api_endpoints.py - Full API flow
   - tests/test_sharepoint_integration.py - Graph API calls
   - tests/test_content_generation_workflow.py - End-to-end generation

3. **Test Fixtures:**
   - Sample brand configurations
   - Mock AI responses
   - Test projects with inputs/outputs

Frontend Tests (Vitest + React Testing Library):

1. **Component Tests:**
   - Button.test.tsx - Interactions and states
   - ProjectCard.test.tsx - Rendering and events
   - ContentGenerationWizard.test.tsx - Step navigation

2. **Integration Tests:**
   - useProjects.test.ts - API hooks
   - BrandContext.test.tsx - Theme switching
   - ContentGenerationFlow.test.tsx - Full wizard flow

3. **E2E Tests (Playwright):**
   - Create project → Upload inputs → Generate content → Download

Setup:
```bash
# Backend
pip install pytest pytest-asyncio pytest-cov httpx

# Frontend
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom
npm install -D @playwright/test
```

Create test commands:
- Backend: `pytest tests/ --cov=app --cov-report=html`
- Frontend: `npm run test` (vitest), `npm run test:e2e` (playwright)

Add CI/CD configuration (.github/workflows/test.yml) for automated testing.""",
            dependencies=[5, 8],
            estimated_time="90 minutes",
            acceptance_criteria=[
                "Backend unit tests created with >70% coverage",
                "Frontend component tests created",
                "E2E test suite functional",
                "CI/CD pipeline runs tests on push",
                "Test commands documented in README"
            ],
            files_to_create=[
                "tests/test_ai_client.py",
                "tests/test_template_engine.py",
                "tests/test_project_manager.py",
                "tests/test_api_endpoints.py",
                "tests/conftest.py",
                "frontend/src/components/UI/Button.test.tsx",
                "frontend/src/components/Dashboard/ProjectCard.test.tsx",
                "frontend/src/hooks/useProjects.test.ts",
                "frontend/tests/e2e/content-generation.spec.ts",
                ".github/workflows/test.yml"
            ],
            files_to_modify=[
                "requirements.txt",
                "frontend/package.json",
                "frontend/vite.config.ts"
            ]
        ))

        self.prompts.append(ImplementationPrompt(
            id=14,
            title="Update documentation and create user guide",
            category=PromptCategory.SETUP,
            priority=PromptPriority.LOW,
            prompt="""Create comprehensive documentation for the AI Tools Creation Application.

Update README.md:

1. **Overview Section:**
   - Project description aligned with Taste OS/Vishwa OS principles
   - Key features (modular dashboard, AI generation, brand consistency)
   - Architecture diagram (update with React frontend)
   - Screenshots of dashboard and content generation

2. **Getting Started:**
   - Prerequisites (Node.js 18+, Python 3.11+, Azure OpenAI API key)
   - Installation steps (backend + frontend)
   - Environment variable configuration
   - First-time setup wizard

3. **User Guide:**
   - Creating your first project
   - Setting up brand identity
   - Generating social media posts
   - Generating PRD documents
   - Downloading and exporting content
   - Managing plugins

4. **Developer Guide:**
   - Project structure explanation
   - Adding new modules
   - Creating custom templates
   - Building plugins
   - API reference (OpenAPI/Swagger)
   - Contributing guidelines

5. **Deployment:**
   - Production build steps
   - Environment configuration
   - Hosting options (Azure, AWS, self-hosted)
   - Windows Service setup (NSSM)
   - Docker containerization

Create additional docs:
- docs/API.md - Complete API reference
- docs/ARCHITECTURE.md - System design details
- docs/PLUGINS.md - Plugin development guide
- docs/DESIGN_SYSTEM.md - UI/UX guidelines
- docs/TROUBLESHOOTING.md - Common issues and solutions

Add inline code documentation:
- Docstrings for all Python functions
- JSDoc comments for TypeScript functions
- Component props documentation

Generate API documentation:
- Use FastAPI's built-in Swagger UI (/docs)
- Create Postman collection for API testing

Record video tutorial (optional):
- Dashboard walkthrough
- Content generation demo
- Brand customization""",
            dependencies=[1, 3, 5, 6],
            estimated_time="60 minutes",
            acceptance_criteria=[
                "README.md updated with complete setup instructions",
                "User guide covers all major features",
                "Developer guide explains architecture",
                "API documentation generated",
                "Troubleshooting guide created",
                "Screenshots and diagrams included"
            ],
            files_to_create=[
                "docs/API.md",
                "docs/ARCHITECTURE.md",
                "docs/PLUGINS.md",
                "docs/DESIGN_SYSTEM.md",
                "docs/TROUBLESHOOTING.md"
            ],
            files_to_modify=[
                "README.md"
            ]
        ))

    def get_prompts_by_priority(self, priority: PromptPriority) -> List[ImplementationPrompt]:
        """Get all prompts of a specific priority"""
        return [p for p in self.prompts if p.priority == priority]

    def get_prompts_by_category(self, category: PromptCategory) -> List[ImplementationPrompt]:
        """Get all prompts of a specific category"""
        return [p for p in self.prompts if p.category == category]

    def get_executable_prompts(self, completed_ids: List[int]) -> List[ImplementationPrompt]:
        """Get prompts whose dependencies are all completed"""
        return [
            p for p in self.prompts
            if p.id not in completed_ids
            and all(dep in completed_ids for dep in p.dependencies)
        ]

    def export_to_json(self, filepath: str):
        """Export all prompts to JSON file"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_prompts": len(self.prompts),
            "prompts": [p.to_dict() for p in self.prompts]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_execution_plan(self, filepath: str):
        """Export prompts in execution order as markdown"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# AI Tools Creation Application - Implementation Plan\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Tasks:** {len(self.prompts)}\n\n")

            # Group by priority
            for priority in [PromptPriority.CRITICAL, PromptPriority.HIGH, PromptPriority.MEDIUM, PromptPriority.LOW]:
                prompts = self.get_prompts_by_priority(priority)
                if not prompts:
                    continue

                f.write(f"## {priority.value.upper()} Priority ({len(prompts)} tasks)\n\n")

                for prompt in prompts:
                    f.write(f"### {prompt.id}. {prompt.title}\n\n")
                    f.write(f"**Category:** {prompt.category.value}  \n")
                    f.write(f"**Estimated Time:** {prompt.estimated_time}  \n")
                    if prompt.dependencies:
                        deps = ", ".join([f"#{d}" for d in prompt.dependencies])
                        f.write(f"**Dependencies:** {deps}  \n")
                    f.write(f"\n**Prompt:**\n\n{prompt.prompt}\n\n")

                    f.write("**Acceptance Criteria:**\n")
                    for criteria in prompt.acceptance_criteria:
                        f.write(f"- [ ] {criteria}\n")
                    f.write("\n")

                    if prompt.files_to_create:
                        f.write("**Files to Create:**\n")
                        for file in prompt.files_to_create:
                            f.write(f"- `{file}`\n")
                        f.write("\n")

                    if prompt.files_to_modify:
                        f.write("**Files to Modify:**\n")
                        for file in prompt.files_to_modify:
                            f.write(f"- `{file}`\n")
                        f.write("\n")

                    f.write("---\n\n")


if __name__ == "__main__":
    generator = PromptGenerator()

    # Export to JSON
    generator.export_to_json("implementation_prompts.json")
    print(f"✓ Generated {len(generator.prompts)} prompts → implementation_prompts.json")

    # Export execution plan
    plan_path = Path("docs") / "auto-implementation" / "IMPLEMENTATION_PLAN.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    generator.export_execution_plan(str(plan_path))
    print(f"✓ Created execution plan → {plan_path}")

    # Show next executable prompts
    completed = []  # Start with no completed tasks
    next_prompts = generator.get_executable_prompts(completed)
    print(f"\n🚀 Ready to execute ({len(next_prompts)} prompts with no dependencies):")
    for p in next_prompts:
        print(f"   #{p.id} - {p.title} ({p.priority.value}, {p.estimated_time})")

# GramaSeva — Verified Civic Complaint & Resolution Platform

**Report local problems. Track progress. Verify real solutions.**

GramaSeva is a digital civic complaint management platform designed to connect citizens, village-level administration and field workers. It helps residents report local infrastructure problems, track complaint progress and view verified resolution updates through a transparent workflow.

## About the Project

Residents often face difficulties reporting local problems such as damaged roads, potholes, water leakage, drainage issues and other public infrastructure concerns. They may not know which authority is responsible or how to follow up after submitting a complaint.

GramaSeva addresses these challenges through a centralized reporting and resolution system.

Citizens can submit complaints with photographs and location details. Authorized administrators review reports, assign work to field workers and verify submitted repair evidence before marking an issue as resolved.

The platform also aims to use AI-assisted image analysis to support complaint categorization and identify possible duplicate reports.

## Key Features

- **Civic Issue Reporting:** Submit complaints with photographs, descriptions and location details.
- **Location Verification:** Capture GPS coordinates or select a location manually.
- **AI-Assisted Classification:** Suggest civic issue categories from uploaded images when AI models are configured.
- **Duplicate Detection:** Identify possible duplicate complaints for human review.
- **Complaint Tracking:** Follow complaint status through a structured timeline.
- **Role-Based Dashboards:** Separate dashboards for Super Admins, Village PDOs, Workers and Citizens.
- **Worker Assignment:** Allow authorized PDOs to assign complaints to approved field workers.
- **Repair Evidence:** Support before-and-after photographs for work verification.
- **Public Transparency:** Display approved complaint information and resolution progress.
- **Multilingual Interface:** Support English, Kannada and Hindi.
- **Notifications:** Provide relevant complaint and administrative updates where configured.

## User Roles

| Role | Responsibilities |
|---|---|
| Super Admin | Manage villages, PDO accounts, access permissions and taluk-level administration. |
| Village PDO | Manage village complaints, workers, assignments and resolution verification. |
| Field Worker | View assigned tasks, update work progress and submit completion evidence. |
| Citizen | Register, report civic problems and track submitted complaints. |
| Public Visitor | View approved public complaint information and progress without logging in. |

## How GramaSeva Works

1. **Report a Problem:** A citizen submits a complaint with an image, description and location.
2. **AI-Assisted Analysis:** The system can suggest an issue category and identify possible duplicate reports.
3. **PDO Review:** The authorized Village PDO reviews the complaint.
4. **Worker Assignment:** An approved field worker receives the task.
5. **Work in Progress:** The worker performs the required repair or maintenance.
6. **Completion Evidence:** The worker uploads after-work photographs and completion details.
7. **Verification:** The PDO or authorized ward member reviews the evidence and updates the resolution status.
8. **Public Update:** Approved resolution information becomes available through the public dashboard.

AI suggestions support the workflow, but authorized people make final decisions about assignments, duplicate complaints and resolution approval.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Database Integration | SQLAlchemy, Psycopg |
| AI/ML Services | Python-based AI model integrations |
| Maps | Existing map integration / configured map provider |
| Deployment | Vercel and Render |

## Project Architecture

The project follows a frontend and backend architecture.

- **apps/web:** Contains the Next.js frontend and user interface.
- **services/api:** Contains the Python FastAPI backend and API services.
- **PostgreSQL:** Stores application data, user information and complaint records.
- **AI Services:** Support image classification and possible duplicate detection.

## Getting Started

To run the project locally, you need:

- Node.js and npm
- Python 3.10 or a compatible supported version
- PostgreSQL
- Git

The frontend and backend have separate dependency and environment configurations. Configure the required database connection, authentication settings and application environment variables before starting the services.

The frontend runs locally on port 3000, and the FastAPI backend runs locally on port 8000. The backend API documentation is available through FastAPI's interactive documentation page.

Refer to the project's configuration files for the exact environment variables and setup requirements.

## AI-Assisted Capabilities

GramaSeva is designed to incorporate AI assistance into civic complaint management.

Potential AI-assisted capabilities include:

- Road damage and pothole image classification.
- Identification of possible duplicate complaint images.
- Visual assistance for before-and-after repair evidence.
- Multilingual text translation.

AI predictions should be treated as suggestions, not official decisions. Model availability, accuracy and production readiness depend on successful integration and testing with representative images.

The core complaint reporting and tracking workflow should remain usable even when AI services are unavailable.

## Security and Privacy

GramaSeva follows important security principles:

- Role-based access control.
- Protected authentication and password handling.
- Village-level and assignment-level authorization.
- Private storage for complaint evidence.
- Controlled access to citizen information.
- Validation of uploaded files.
- Human review before final complaint resolution.
- Protection of sensitive information on public dashboards.

Only approved and privacy-safe complaint information should be visible to public visitors.

## Future Improvements

- Improved AI classification using locally relevant civic issue images.
- More reliable duplicate complaint matching.
- Better before-and-after repair evidence analysis.
- Additional multilingual and voice-based accessibility.
- Improved map-based village and ward identification.
- Enhanced analytics for administrative decision-making.
- Production-ready notification and monitoring services.

## Project Vision

Our vision is to make civic problem reporting more accessible, accountable and transparent.

By connecting citizens, local administration and field workers through a structured digital workflow, GramaSeva aims to help communities report problems, monitor progress and build greater trust in local civic services.

## Contributing

Contributions, suggestions and feedback are welcome.

We encourage developers to explore the repository, identify improvements, report issues and contribute to making civic services more accessible and transparent.

## Project Information

**Project Name:** GramaSeva  
**Category:** Civic Technology / GovTech  
**Focus:** Village and Ward Civic Issue Reporting and Resolution  
**Repository:** [GitHub – GramaSeva](https://github.com/RavikumarPujari/GramaSeva)

---

*GramaSeva is a community-focused project. It is not an official government website or a replacement for established government grievance channels.*

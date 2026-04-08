workspace "SQL-to-ARC Middleware" "Middleware component to convert SQL views into Annotated Research Context (ARC) objects." {

    model {
        user = person "RDI Data Manager" "Responsible for managing and providing metadata from a Research Data Infrastructure."

        group "FAIRagro Ecosystem" {
            fairAgroApi = softwareSystem "FAIRagro Middleware API" "Receives RO-Crate JSON-LD payloads." "External"
        }

        sqlToArc = softwareSystem "SQL-to-ARC Converter" "Central component that maps relational data to ARC objects and sends them to the API." {
            database = container "RDI SQL Database" "PostgreSQL database serving standardized metadata views." "PostgreSQL" "Database"
            
            converter = container "Converter Service" "Core logic for database extraction, mapping, and API transmission." "Python" {
                main = component "Main Entry Point" "CLI interface and orchestrator." "Python"
                
                group "Async IO Loop (Controller)" {
                    orchestrator = component "Workflow Orchestrator" "Coordinates the data flow, manages concurrent tasks via Semaphores." "Python/Asyncio"
                    stats = component "Processing Stats" "Collects success/failure metrics and generates final reports." "Python"
                }

                group "Process Pool Executor (Worker)" {
                    mapper = component "ARC Mapper" "Transforms relational rows into ARC structures using arctrl. Runs in separate OS processes to bypass GIL." "Python/arctrl"
                    serializer = component "JSON-LD Serializer" "Converts ARC objects to JSON strings directly in the worker process." "Python"
                }

                group "Streaming Generator (Data Layer)" {
                    db_client = component "Database Client" "Implements lazy-loading and relational batching via SQLAlchemy streaming cursors." "Python/SQLAlchemy"
                }

                api_client = component "API Client" "Handles mTLS secured async HTTP uploads to the Middleware API." "Python/httpx"
            }

            demo_api = container "Mock API" "Simulates the FAIRagro API for local testing and CI." "FastAPI" "Development"
        }

        # Relationships
        user -> main "Configures and starts"
        
        main -> orchestrator "Orchestrates through"
        orchestrator -> db_client "Streams investigations from"
        orchestrator -> mapper "Submits tasks to Process Pool"
        orchestrator -> api_client "Enqueues uploads to"
        orchestrator -> stats "Updates metrics in"
        
        mapper -> serializer "Serializes to JSON-LD via"
        db_client -> database "Queries views (vInvestigation, vStudy, etc.)"
        api_client -> fairAgroApi "Sends RO-Crate JSON-LD (mTLS)"
        api_client -> demo_api "Sends data during local demo"
    }

    views {
        systemContext sqlToArc "SystemContext" {
            include *
            autoLayout
        }

        container sqlToArc "Containers" {
            include *
            autoLayout
        }

        component converter "Components" {
            include *
            autoLayout
        }

        styles {
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Database" {
                shape Cylinder
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Group" {
                color #666666
                border Dotted
            }
        }
    }
}

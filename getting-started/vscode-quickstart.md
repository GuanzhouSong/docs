---
title: Visual Studio Code Quick Start
description: Get started with DocumentDB using the Visual Studio Code extension for a seamless development experience.
---

# VS Code Extension Quick Start

Get started with DocumentDB using the Visual Studio Code extension for a seamless development experience.

## Prerequisites

- Visual Studio Code installed
- Docker Desktop installed and running
- Basic familiarity with document databases
- Git installed (for cloning the repository)

## Installing the Extension

1. Open VS Code
2. Navigate to the Extensions marketplace (Ctrl+Shift+X or Cmd+Shift+X)
3. Search for "DocumentDB for VS Code"
4. Click Install
5. Reload VS Code if prompted

## Setting Up Your First Database

1. Creating a new DocumentDB instance

   **Bash**

   ```bash
   docker pull ghcr.io/documentdb/documentdb/documentdb-local:latest
   docker tag ghcr.io/documentdb/documentdb/documentdb-local:latest documentdb
   read -r -p 'DocumentDB username: ' DOCUMENTDB_USERNAME
   read -r -s -p 'DocumentDB password: ' DOCUMENTDB_PASSWORD
   printf '\n'
   export DOCUMENTDB_USERNAME DOCUMENTDB_PASSWORD
   if docker run -dt -p 127.0.0.1:10260:10260 --name documentdb-container documentdb --username "${DOCUMENTDB_USERNAME:?DocumentDB username cannot be empty}" --password "${DOCUMENTDB_PASSWORD:?DocumentDB password cannot be empty}"; then
     docker image rm -f ghcr.io/documentdb/documentdb/documentdb-local:latest || echo "No existing documentdb image to remove"
   fi
   ```

   **PowerShell**

   ```powershell
   docker pull ghcr.io/documentdb/documentdb/documentdb-local:latest
   docker tag ghcr.io/documentdb/documentdb/documentdb-local:latest documentdb
   $env:DOCUMENTDB_USERNAME = Read-Host 'DocumentDB username'
   $securePassword = Read-Host 'DocumentDB password' -AsSecureString
   $env:DOCUMENTDB_PASSWORD = [System.Net.NetworkCredential]::new('', $securePassword).Password
   if ([string]::IsNullOrWhiteSpace($env:DOCUMENTDB_USERNAME) -or [string]::IsNullOrWhiteSpace($env:DOCUMENTDB_PASSWORD)) {
       throw 'DocumentDB credentials cannot be empty'
   } else {
       docker run -dt -p 127.0.0.1:10260:10260 --name documentdb-container documentdb --username "$env:DOCUMENTDB_USERNAME" --password "$env:DOCUMENTDB_PASSWORD"
       if ($LASTEXITCODE -eq 0) {
           docker image rm -f ghcr.io/documentdb/documentdb/documentdb-local:latest
           if ($LASTEXITCODE -ne 0) { echo "No existing documentdb image to remove" }
       }
   }
   ```

   > **Note:** During the transition to the Linux Foundation, Docker images may still be hosted on Microsoft's container registry. These will be migrated to the new DocumentDB organization as the transition completes.
   >
   > **Note:** Both versions prompt for credentials and reject empty values so the container cannot fall through to the public `default_user` / `Admin100` defaults. Enter the same values when the extension asks for the local connection credentials.
   >
   > **Network Note:** The example binds the gateway only to the local host. Expose it to other machines only after adding firewall rules and a certificate those clients can validate.
   >
   > **Port Note:** To use host port `27017` while leaving the gateway on its default container port, publish `-p 127.0.0.1:27017:10260` and enter `27017` in the extension. To change the gateway's internal port too, add `--documentdb-port 27017` after the image name and publish that container port.

2. Connecting to your database
   - Locate and select the DocumentDB icon in the primary VS Code sidebar on the left-hand side.
   - Add a new connection to your DocumentDB:
     - In the DocumentDB Connections area, locate and expand the **DocumentDB Local** node.
     - Select the **New Local Connection** option.
     - Confirm the port (default value `10260`), username, password, and choose the **Disable TLS/SSL** option.
     - **Note:** TLS/SSL can be enabled, but this walkthrough skips those steps for simplicity.
     - A new DocumentDB Local entry will be added and listed in your DocumentDB Connections area.

3. Creating your first database and collection
   - Click on the drop-down next to your local connection and select "Create Database..."
   - Enter database name and confirm
   - Click on the drop-down next to your created database and select "Create Collection..."
   - Enter collection name and confirm
   - Repeat for every database and collection you wish to create under your connection

## Working with Documents

1. Creating documents
   - Use the Table View for quick data entry
   - Use the Tree View for hierarchical data exploration
   - Use the JSON View for detailed document structure
   ```json
   {
     "name": "Test Document",
     "type": "example",
     "created_at": { "$date": "2026-08-25T00:00:00Z" }
   }
   ```

2. Using the document explorer
   - Browse documents in multiple views:
     - Table View for quick insights
     - Tree View for hierarchical exploration
     - JSON View for detailed structure
   - Use smooth pagination for large datasets

## Import and Export

1. Importing data
   - Click on the "Import" button on each collection
   - Choose your JSON file
   - Confirm import

2. Exporting data
   - Export entire collections or query results using the "Export" button on each collection

## Debugging and Troubleshooting

1. Common issues and solutions

2. Using the extension logs

3. Getting support
   - Visit our [GitHub repository](https://github.com/microsoft/vscode-documentdb)
   - Join the community on [Discord](https://discord.gg/vH7bYu524D)
   - Check documentation

## Next Steps

- Explore advanced querying capabilities in the [API Reference](https://documentdb.io/docs/reference/)
- Connect your application using the [Python Setup for DocumentDB](https://documentdb.io/docs/getting-started/python-setup/) 

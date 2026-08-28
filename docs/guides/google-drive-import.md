# Google Drive Import

PRISM can preview and import numbered answer-paper images from a teacher-selected Google Drive folder. OAuth access remains in browser memory and the backend does not persist the access token.

## Google Cloud Setup

Create a Google Cloud project and configure:

1. Google Drive API
2. Google Picker API
3. OAuth consent screen
4. OAuth 2.0 Web application client
5. Browser API key restricted to the expected web origins and required APIs

Register every frontend origin, including `http://localhost:3000` for local development and the exact HTTPS production origin.

Set backend and frontend values:

```dotenv
GOOGLE_DRIVE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
NEXT_PUBLIC_GOOGLE_DRIVE_API_KEY=your-restricted-browser-api-key
NEXT_PUBLIC_GOOGLE_DRIVE_APP_ID=your-google-cloud-project-number
NEXT_PUBLIC_GOOGLE_DRIVE_SCOPE=https://www.googleapis.com/auth/drive.readonly
```

The `NEXT_PUBLIC_*` values are compiled into the browser bundle. They are identifiers or a restricted browser key, not private credentials. Apply HTTP referrer and API restrictions to the key.

## Supported Folder Shapes

### Main Folder

Select a folder whose descendants represent students:

```text
Engineering Economics Papers/
|-- Ananya Rao/
|   |-- 1.jpg
|   |-- 2.jpg
|   `-- 3.png
|-- Dev Menon/
|   |-- scans/
|   |   |-- 1.jpg
|   |   `-- 2.jpg
|   `-- notes.txt
`-- Farah Ali/
    `-- 1.jpg
```

PRISM searches recursively up to six folder levels and uses JPEG or PNG files whose basename is numeric. It sorts pages numerically. Other files are ignored.

### Direct Student Folder

Select one student's folder when importing a single paper. The preview treats the selected folder as the paper source rather than searching for multiple student folders beneath it.

## Preview

Select **Choose main folder** or **Choose student folder** from an exam. After Google authorization and folder selection, the backend creates a persisted preview batch containing discovered items and page manifests.

For each item, choose one action:

- match an existing roster student
- create a new student from the folder name
- skip the folder

Preview does not create submissions or download every source file.

## Commit

Committing the batch downloads selected pages serially, sends them through the normal upload validation path, creates submissions, and queues in-process assessment tasks.

Current limits and behavior:

- up to 200 student folders per preview
- up to 500 visited folders across recursive traversal
- only JPEG and PNG page files
- OAuth scope defaults to Drive read-only
- shared-drive query flags are supported
- each committed item can succeed or fail independently
- the batch can be marked complete even if an individual item failed, so inspect resulting submissions

## Security Notes

- Use read-only Drive scope.
- Restrict the browser API key by origin and API.
- Never place an OAuth client secret in frontend variables.
- Do not paste access tokens into logs, issues, screenshots, or documentation.
- Review Google consent-screen publication and organization policy before production use.
- Treat folder names and page images as educational records.

## Troubleshooting

### Picker Does Not Open

Confirm all frontend variables were present during `npm run build`. Public variables are build-time values in the current Docker image.

### Origin Or App Errors

Verify the exact scheme, host, and port in Google Cloud. `http://localhost:3000` and an HTTPS production origin are separate registrations.

### Empty Preview

Confirm images use numeric filenames such as `1.jpg`, `2.png`, and `10.jpg`. Files like `page-1.jpg` are not imported.

### Missing Nested Pages

Confirm the page is within six folder levels of the selected student folder and that traversal has not exceeded the visited-folder cap.

### Authorization Expired

Select the folder again to acquire a new browser token. Tokens are deliberately not stored in PRISM.

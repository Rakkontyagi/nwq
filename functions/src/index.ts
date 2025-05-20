import * as admin from "firebase-admin";

// Initialize Firebase Admin SDK
if (admin.apps.length === 0) {
  admin.initializeApp();
}

// Export all functions from other modules
export * from "./auth"; // This will export promoteUserToAdmin and listAllUsers
export * from "./platforms"; // Add this line to export platform functions
export * from "./content_templates"; // Add this line
export * from "./websites"; // Add this line

// You can add other general purpose functions here or export from other files
// For example, if helloWorld was still relevant:
// import * as functions from "firebase-functions";
// export const helloWorld = functions.https.onCall((data, context) => {
//   functions.logger.info("Hello logs!", {structuredData: true});
//   return {message: "Hello from Firebase by an admin!"};
// });

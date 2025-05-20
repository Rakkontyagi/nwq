import * as admin from "firebase-admin";
import *_firebase_functions from "firebase-functions"; // Renamed to avoid conflict

// It's good practice to use a consistent logger instance
const functions = _firebase_functions; 
const logger = functions.logger;

/**
 * Sets a custom claim { admin: true } for a user.
 * This function should only be callable by users who are already admins.
 */
export const promoteUserToAdmin = functions.https.onCall(async (data, context) => {
  // Check if the caller is authenticated and is an admin.
  if (!context.auth) {
    throw new functions.https.HttpsError(
      "unauthenticated",
      "The function must be called while authenticated."
    );
  }
  if (context.auth.token.admin !== true) {
    throw new functions.https.HttpsError(
      "permission-denied",
      "The function must be called by an admin user."
    );
  }

  const { uid } = data;
  if (!uid || typeof uid !== "string") {
    throw new functions.https.HttpsError(
      "invalid-argument",
      "The function must be called with a 'uid' argument."
    );
  }

  try {
    await admin.auth().setCustomUserClaims(uid, { admin: true });
    logger.info(`Successfully set admin claim for user: ${uid}`);
    return { message: `Success! User ${uid} is now an admin.` };
  } catch (error) {
    logger.error(`Error setting admin claim for user ${uid}:`, error);
    throw new functions.https.HttpsError(
      "internal",
      "Unable to set admin claim.",
      error
    );
  }
});

/**
 * Lists all users.
 * This function should only be callable by users who are admins.
 */
export const listAllUsers = functions.https.onCall(async (data, context) => {
  if (!context.auth) {
    throw new functions.https.HttpsError(
      "unauthenticated",
      "The function must be called while authenticated."
    );
  }
  if (context.auth.token.admin !== true) {
    throw new functions.https.HttpsError(
      "permission-denied",
      "The function must be called by an admin user."
    );
  }

  try {
    const listUsersResult = await admin.auth().listUsers(1000); // Max 1000 per page
    const users = listUsersResult.users.map((userRecord) => ({
      uid: userRecord.uid,
      email: userRecord.email,
      displayName: userRecord.displayName,
      customClaims: userRecord.customClaims,
      disabled: userRecord.disabled,
      metadata: {
        lastSignInTime: userRecord.metadata.lastSignInTime,
        creationTime: userRecord.metadata.creationTime,
      }
    }));
    // TODO: Implement pagination if more than 1000 users are expected.
    return { users };
  } catch (error) {
    logger.error("Error listing users:", error);
    throw new functions.https.HttpsError(
      "internal",
      "Unable to list users.",
      error
    );
  }
});

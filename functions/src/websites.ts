import * as admin from "firebase-admin";
import *_firebase_functions from "firebase-functions";

const functions = _firebase_functions;
const logger = functions.logger;
const db = admin.firestore();

const WEBSITES_COLLECTION = "websites";

// Helper to check for admin privileges
const ensureAdmin = (context: functions.https.CallableContext) => {
  if (!context.auth || context.auth.token.admin !== true) {
    throw new functions.https.HttpsError(
      "permission-denied",
      "The function must be called by an admin user."
    );
  }
};

// Interface for Website data
interface WebsiteData {
  domain: string;
  title?: string;
  description?: string;
  keywords?: string[];
  // created_at will be handled by the server
}

export const createWebsite = functions.https.onCall(async (data: WebsiteData, context) => {
  ensureAdmin(context);

  if (!data.domain) {
    throw new functions.https.HttpsError(
      "invalid-argument",
      "Missing required field: domain."
    );
  }

  try {
    const newWebsiteRef = await db.collection(WEBSITES_COLLECTION).add({
      ...data,
      keywords: data.keywords || [], // Ensure keywords is an array
      created_at: admin.firestore.FieldValue.serverTimestamp(),
    });
    logger.info(`Website created with ID: ${newWebsiteRef.id}`, data);
    return { id: newWebsiteRef.id, ...data };
  } catch (error) {
    logger.error("Error creating website:", error, data);
    throw new functions.https.HttpsError("internal", "Could not create website.", error);
  }
});

export const getWebsite = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing website ID.");
  }
  try {
    const doc = await db.collection(WEBSITES_COLLECTION).doc(data.id).get();
    if (!doc.exists) {
      throw new functions.https.HttpsError("not-found", "Website not found.");
    }
    return { id: doc.id, ...doc.data() };
  } catch (error) {
    logger.error(`Error getting website ${data.id}:`, error);
    if (error instanceof functions.https.HttpsError) throw error;
    throw new functions.https.HttpsError("internal", "Could not retrieve website.", error);
  }
});

export const listWebsites = functions.https.onCall(async (data, context) => {
  ensureAdmin(context);
  try {
    const snapshot = await db.collection(WEBSITES_COLLECTION).orderBy("domain").get();
    const websites = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    return { websites };
  } catch (error) {
    logger.error("Error listing websites:", error);
    throw new functions.https.HttpsError("internal", "Could not list websites.", error);
  }
});

export const updateWebsite = functions.https.onCall(async (data: { id: string } & Partial<WebsiteData>, context) => {
  ensureAdmin(context);
  const { id, ...updateData } = data;
  if (!id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing website ID for update.");
  }
  if (Object.keys(updateData).length === 0) {
    throw new functions.https.HttpsError("invalid-argument", "No update data provided.");
  }
  if (updateData.keywords && !Array.isArray(updateData.keywords)) {
    updateData.keywords = []; // Or handle error
  }

  try {
    await db.collection(WEBSITES_COLLECTION).doc(id).update({
        ...updateData,
        updated_at: admin.firestore.FieldValue.serverTimestamp()
    });
    logger.info(`Website updated for ID: ${id}`, updateData);
    return { message: "Website updated successfully.", id };
  } catch (error) {
    logger.error(`Error updating website ${id}:`, error, updateData);
    throw new functions.https.HttpsError("internal", "Could not update website.", error);
  }
});

export const deleteWebsite = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing website ID for deletion.");
  }
  try {
    await db.collection(WEBSITES_COLLECTION).doc(data.id).delete();
    logger.info(`Website deleted with ID: ${data.id}`);
    return { message: "Website deleted successfully.", id: data.id };
  } catch (error) {
    logger.error(`Error deleting website ${data.id}:`, error);
    throw new functions.https.HttpsError("internal", "Could not delete website.", error);
  }
});

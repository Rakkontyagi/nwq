import * as admin from "firebase-admin";
import *_firebase_functions from "firebase-functions"; // Renamed to avoid conflict

const functions = _firebase_functions; 
const logger = functions.logger;
const db = admin.firestore(); // Firestore instance

const PLATFORMS_COLLECTION = "platforms";

// Helper to check for admin privileges
const ensureAdmin = (context: functions.https.CallableContext) => {
  if (!context.auth || context.auth.token.admin !== true) {
    throw new functions.https.HttpsError(
      "permission-denied",
      "The function must be called by an admin user."
    );
  }
};

// Interface for Platform data (optional but good practice)
interface PlatformData {
  name: string;
  url: string;
  platform_type: 'blog' | 'forum' | 'profile' | 'pdf' | 'image' | 'rss';
  requires_content: boolean;
  requires_media: boolean;
  media_type?: string | null;
  estimated_da?: number | null;
  estimated_spam_score?: number | null;
  active: boolean;
  // created_at will be handled by the server
}

export const createPlatform = functions.https.onCall(async (data: PlatformData, context) => {
  ensureAdmin(context);

  // Basic validation
  if (!data.name || !data.url || !data.platform_type) {
    throw new functions.https.HttpsError(
      "invalid-argument",
      "Missing required fields: name, url, platform_type."
    );
  }

  try {
    const newPlatformRef = await db.collection(PLATFORMS_COLLECTION).add({
      ...data,
      created_at: admin.firestore.FieldValue.serverTimestamp(),
    });
    logger.info(`Platform created with ID: ${newPlatformRef.id}`, data);
    return { id: newPlatformRef.id, ...data };
  } catch (error) {
    logger.error("Error creating platform:", error, data);
    throw new functions.https.HttpsError("internal", "Could not create platform.", error);
  }
});

export const getPlatform = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing platform ID.");
  }
  try {
    const doc = await db.collection(PLATFORMS_COLLECTION).doc(data.id).get();
    if (!doc.exists) {
      throw new functions.https.HttpsError("not-found", "Platform not found.");
    }
    return { id: doc.id, ...doc.data() };
  } catch (error) {
    logger.error(`Error getting platform ${data.id}:`, error);
    if (error instanceof functions.https.HttpsError) throw error;
    throw new functions.https.HttpsError("internal", "Could not retrieve platform.", error);
  }
});

export const listPlatforms = functions.https.onCall(async (data, context) => {
  ensureAdmin(context);
  try {
    const snapshot = await db.collection(PLATFORMS_COLLECTION).orderBy("name").get();
    const platforms = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    return { platforms };
  } catch (error) {
    logger.error("Error listing platforms:", error);
    throw new functions.https.HttpsError("internal", "Could not list platforms.", error);
  }
});

export const updatePlatform = functions.https.onCall(async (data: { id: string } & Partial<PlatformData>, context) => {
  ensureAdmin(context);
  const { id, ...updateData } = data;
  if (!id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing platform ID for update.");
  }
  if (Object.keys(updateData).length === 0) {
    throw new functions.https.HttpsError("invalid-argument", "No update data provided.");
  }

  try {
    await db.collection(PLATFORMS_COLLECTION).doc(id).update({
        ...updateData,
        updated_at: admin.firestore.FieldValue.serverTimestamp() // Optional: track updates
    });
    logger.info(`Platform updated for ID: ${id}`, updateData);
    return { message: "Platform updated successfully.", id };
  } catch (error) {
    logger.error(`Error updating platform ${id}:`, error, updateData);
    throw new functions.https.HttpsError("internal", "Could not update platform.", error);
  }
});

export const deletePlatform = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing platform ID for deletion.");
  }
  try {
    await db.collection(PLATFORMS_COLLECTION).doc(data.id).delete();
    logger.info(`Platform deleted with ID: ${data.id}`);
    return { message: "Platform deleted successfully.", id: data.id };
  } catch (error) {
    logger.error(`Error deleting platform ${data.id}:`, error);
    throw new functions.https.HttpsError("internal", "Could not delete platform.", error);
  }
});

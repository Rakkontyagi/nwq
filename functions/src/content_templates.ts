import * as admin from "firebase-admin";
import *_firebase_functions from "firebase-functions"; // Renamed to avoid conflict

const functions = _firebase_functions;
const logger = functions.logger;
const db = admin.firestore();

const CONTENT_TEMPLATES_COLLECTION = "content_templates";

// Helper to check for admin privileges
const ensureAdmin = (context: functions.https.CallableContext) => {
  if (!context.auth || context.auth.token.admin !== true) {
    throw new functions.https.HttpsError(
      "permission-denied",
      "The function must be called by an admin user."
    );
  }
};

// Interface for ContentTemplate data
interface ContentTemplateData {
  name: string;
  content_type: 'article' | 'profile' | 'description'; // As per schema
  template: string; // The content template with placeholders
  variables?: string[]; // List of variable names used in template
  platform_type?: string; // Suggests which platform this template is suitable for
  // created_at will be handled by the server
}

export const createContentTemplate = functions.https.onCall(async (data: ContentTemplateData, context) => {
  ensureAdmin(context);

  if (!data.name || !data.content_type || !data.template) {
    throw new functions.https.HttpsError(
      "invalid-argument",
      "Missing required fields: name, content_type, template."
    );
  }

  try {
    const newTemplateRef = await db.collection(CONTENT_TEMPLATES_COLLECTION).add({
      ...data,
      variables: data.variables || [], // Ensure variables is an array
      created_at: admin.firestore.FieldValue.serverTimestamp(),
    });
    logger.info(`Content template created with ID: ${newTemplateRef.id}`, data);
    return { id: newTemplateRef.id, ...data };
  } catch (error) {
    logger.error("Error creating content template:", error, data);
    throw new functions.https.HttpsError("internal", "Could not create content template.", error);
  }
});

export const getContentTemplate = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing content template ID.");
  }
  try {
    const doc = await db.collection(CONTENT_TEMPLATES_COLLECTION).doc(data.id).get();
    if (!doc.exists) {
      throw new functions.https.HttpsError("not-found", "Content template not found.");
    }
    return { id: doc.id, ...doc.data() };
  } catch (error) {
    logger.error(`Error getting content template ${data.id}:`, error);
    if (error instanceof functions.https.HttpsError) throw error;
    throw new functions.https.HttpsError("internal", "Could not retrieve content template.", error);
  }
});

export const listContentTemplates = functions.https.onCall(async (data, context) => {
  ensureAdmin(context);
  try {
    // Optional: Add filtering/pagination parameters from 'data' if needed
    const snapshot = await db.collection(CONTENT_TEMPLATES_COLLECTION).orderBy("name").get();
    const templates = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    return { templates };
  } catch (error)
  {
    logger.error("Error listing content templates:", error);
    throw new functions.https.HttpsError("internal", "Could not list content templates.", error);
  }
});

export const updateContentTemplate = functions.https.onCall(async (data: { id: string } & Partial<ContentTemplateData>, context) => {
  ensureAdmin(context);
  const { id, ...updateData } = data;
  if (!id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing content template ID for update.");
  }
  if (Object.keys(updateData).length === 0) {
    throw new functions.https.HttpsError("invalid-argument", "No update data provided.");
  }
   if (updateData.variables && !Array.isArray(updateData.variables)) {
    updateData.variables = []; // Or handle error appropriately
  }

  try {
    await db.collection(CONTENT_TEMPLATES_COLLECTION).doc(id).update({
        ...updateData,
        updated_at: admin.firestore.FieldValue.serverTimestamp()
    });
    logger.info(`Content template updated for ID: ${id}`, updateData);
    return { message: "Content template updated successfully.", id };
  } catch (error) {
    logger.error(`Error updating content template ${id}:`, error, updateData);
    throw new functions.https.HttpsError("internal", "Could not update content template.", error);
  }
});

export const deleteContentTemplate = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing content template ID for deletion.");
  }
  try {
    await db.collection(CONTENT_TEMPLATES_COLLECTION).doc(data.id).delete();
    logger.info(`Content template deleted with ID: ${data.id}`);
    return { message: "Content template deleted successfully.", id: data.id };
  } catch (error) {
    logger.error(`Error deleting content template ${data.id}:`, error);
    throw new functions.https.HttpsError("internal", "Could not delete content template.", error);
  }
});

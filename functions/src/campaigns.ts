import * as admin from "firebase-admin";
import *_firebase_functions from "firebase-functions";

const functions = _firebase_functions;
const logger = functions.logger;
const db = admin.firestore();

const CAMPAIGNS_COLLECTION = "campaigns";
const WEBSITES_COLLECTION = "websites"; // For validation

// Helper to check for admin privileges
const ensureAdmin = (context: functions.https.CallableContext) => {
  if (!context.auth || context.auth.token.admin !== true) {
    throw new functions.https.HttpsError(
      "permission-denied",
      "The function must be called by an admin user."
    );
  }
};

// Interface for Campaign data
interface CampaignData {
  website_id: string; // Reference to websites collection
  name: string;
  target_url: string;
  anchor_text?: string[];
  keywords?: string[];
  status: 'active' | 'paused' | 'draft' | 'completed'; // As per schema
  max_links_per_day?: number;
  // created_at will be handled by the server
}

// Helper function to validate website_id existence
const validateWebsiteExists = async (websiteId: string) => {
  const websiteDoc = await db.collection(WEBSITES_COLLECTION).doc(websiteId).get();
  if (!websiteDoc.exists) {
    throw new functions.https.HttpsError(
      "not-found",
      `Invalid website_id: Website document with ID ${websiteId} does not exist.`
    );
  }
};

export const createCampaign = functions.https.onCall(async (data: CampaignData, context) => {
  ensureAdmin(context);

  const { website_id, name, target_url, status } = data;
  if (!website_id || !name || !target_url || !status) {
    throw new functions.https.HttpsError(
      "invalid-argument",
      "Missing required fields: website_id, name, target_url, status."
    );
  }

  await validateWebsiteExists(website_id);

  try {
    const newCampaignRef = await db.collection(CAMPAIGNS_COLLECTION).add({
      ...data,
      anchor_text: data.anchor_text || [],
      keywords: data.keywords || [],
      max_links_per_day: data.max_links_per_day || 0,
      created_at: admin.firestore.FieldValue.serverTimestamp(),
    });
    logger.info(`Campaign created with ID: ${newCampaignRef.id}`, data);
    return { id: newCampaignRef.id, ...data };
  } catch (error) {
    logger.error("Error creating campaign:", error, data);
    if (error instanceof functions.https.HttpsError) throw error;
    throw new functions.https.HttpsError("internal", "Could not create campaign.", error);
  }
});

export const getCampaign = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing campaign ID.");
  }
  try {
    const doc = await db.collection(CAMPAIGNS_COLLECTION).doc(data.id).get();
    if (!doc.exists) {
      throw new functions.https.HttpsError("not-found", "Campaign not found.");
    }
    return { id: doc.id, ...doc.data() };
  } catch (error) {
    logger.error(`Error getting campaign ${data.id}:`, error);
    if (error instanceof functions.https.HttpsError) throw error;
    throw new functions.https.HttpsError("internal", "Could not retrieve campaign.", error);
  }
});

export const listCampaigns = functions.https.onCall(async (data: { websiteId?: string }, context) => {
  ensureAdmin(context);
  try {
    let query: admin.firestore.Query = db.collection(CAMPAIGNS_COLLECTION);
    if (data.websiteId) {
      logger.info(`Listing campaigns for website ID: ${data.websiteId}`);
      query = query.where("website_id", "==", data.websiteId);
    }
    query = query.orderBy("name");
    const snapshot = await query.get();
    const campaigns = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    return { campaigns };
  } catch (error) {
    logger.error("Error listing campaigns:", error);
    throw new functions.https.HttpsError("internal", "Could not list campaigns.", error);
  }
});

export const updateCampaign = functions.https.onCall(async (data: { id: string } & Partial<CampaignData>, context) => {
  ensureAdmin(context);
  const { id, website_id, ...updateData } = data;
  if (!id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing campaign ID for update.");
  }
  if (Object.keys(updateData).length === 0 && !website_id) { // also check website_id as it's handled separately
    throw new functions.https.HttpsError("invalid-argument", "No update data provided.");
  }

  if (website_id) { // If website_id is being updated, validate it
    await validateWebsiteExists(website_id);
  }
  
  const finalUpdateData: any = { ...updateData };
  if (website_id) {
    finalUpdateData.website_id = website_id;
  }
  if (updateData.anchor_text && !Array.isArray(updateData.anchor_text)) {
    finalUpdateData.anchor_text = [];
  }
  if (updateData.keywords && !Array.isArray(updateData.keywords)) {
    finalUpdateData.keywords = [];
  }

  try {
    await db.collection(CAMPAIGNS_COLLECTION).doc(id).update({
        ...finalUpdateData,
        updated_at: admin.firestore.FieldValue.serverTimestamp()
    });
    logger.info(`Campaign updated for ID: ${id}`, finalUpdateData);
    return { message: "Campaign updated successfully.", id };
  } catch (error) {
    logger.error(`Error updating campaign ${id}:`, error, finalUpdateData);
    if (error instanceof functions.https.HttpsError) throw error;
    throw new functions.https.HttpsError("internal", "Could not update campaign.", error);
  }
});

export const deleteCampaign = functions.https.onCall(async (data: { id: string }, context) => {
  ensureAdmin(context);
  if (!data.id) {
    throw new functions.https.HttpsError("invalid-argument", "Missing campaign ID for deletion.");
  }
  try {
    // Consider deleting related tasks or backlinks, or handle that via background triggers.
    // For now, direct deletion of the campaign document.
    await db.collection(CAMPAIGNS_COLLECTION).doc(data.id).delete();
    logger.info(`Campaign deleted with ID: ${data.id}`);
    return { message: "Campaign deleted successfully.", id: data.id };
  } catch (error) {
    logger.error(`Error deleting campaign ${data.id}:`, error);
    throw new functions.https.HttpsError("internal", "Could not delete campaign.", error);
  }
});

import * as admin from "firebase-admin";
import *_firebase_functions from "firebase-functions";

// NEW Import:
import { PlatformHandlerFactory, TaskPayload, SubmissionResult, VerificationResult } from "../handlers";


const functions = _firebase_functions;
const logger = functions.logger;
const db = admin.firestore();

const TASKS_COLLECTION = "tasks";
const CAMPAIGNS_COLLECTION = "campaigns"; // Exists
const PLATFORMS_COLLECTION = "platforms"; // Exists
// const BACKLINKS_COLLECTION = "backlinks"; // For future use with backlink_id validation in enqueueTask

// Helper to check for admin privileges
const ensureAdmin = (context: functions.https.CallableContext) => {
  if (!context.auth || context.auth.token.admin !== true) {
    throw new functions.https.HttpsError(
      "permission-denied",
      "The function must be called by an admin user."
    );
  }
};

// Interface for Task data (as per schema, plus some defaults)
interface TaskData {
  campaign_id: string; // Reference to campaigns
  platform_id: string; // Reference to platforms
  backlink_id?: string | null; // Reference to backlinks (optional at enqueue time)
  task_type: 'submission' | 'verification';
  status?: 'pending' | 'processing' | 'completed' | 'failed'; // Default to 'pending'
  priority?: number; // Default to 0 or 1
  scheduled_for?: admin.firestore.Timestamp | string; // Can be a timestamp or ISO string
  // started_at, completed_at, result, retry_count will be set by worker or later processes
}

// Helper function to validate document existence
const validateDocExists = async (collection: string, docId: string, docName: string) => {
  const doc = await db.collection(collection).doc(docId).get();
  if (!doc.exists) {
    throw new functions.https.HttpsError(
      "not-found",
      `Invalid ${docName}_id: ${docName} document with ID ${docId} does not exist.`
    );
  }
};

export const enqueueTask = functions.https.onCall(async (data: TaskData, context) => {
  ensureAdmin(context);

  const { campaign_id, platform_id, task_type } = data;
  if (!campaign_id || !platform_id || !task_type) {
    throw new functions.https.HttpsError(
      "invalid-argument",
      "Missing required fields: campaign_id, platform_id, task_type."
    );
  }

  // Validate references
  await validateDocExists(CAMPAIGNS_COLLECTION, campaign_id, "campaign");
  await validateDocExists(PLATFORMS_COLLECTION, platform_id, "platform");
  if (data.backlink_id) {
      // Validation for backlink_id can be added here if needed, e.g.,
      // await validateDocExists(BACKLINKS_COLLECTION, data.backlink_id, "backlink");
  }


  let scheduledForTimestamp: admin.firestore.Timestamp;
  if (data.scheduled_for) {
    if (typeof data.scheduled_for === 'string') {
      scheduledForTimestamp = admin.firestore.Timestamp.fromDate(new Date(data.scheduled_for));
    } else {
      scheduledForTimestamp = data.scheduled_for as admin.firestore.Timestamp;
    }
  } else {
    scheduledForTimestamp = admin.firestore.Timestamp.now();
  }

  const newTaskData = {
    ...data,
    status: data.status || 'pending',
    priority: data.priority || 1,
    scheduled_for: scheduledForTimestamp,
    created_at: admin.firestore.FieldValue.serverTimestamp(),
    retry_count: 0,
  };

  try {
    const newTaskRef = await db.collection(TASKS_COLLECTION).add(newTaskData);
    logger.info(`Task enqueued with ID: ${newTaskRef.id}`, newTaskData);
    return { id: newTaskRef.id, ...newTaskData };
  } catch (error) {
    logger.error("Error enqueueing task:", error, newTaskData);
    if (error instanceof functions.https.HttpsError) throw error;
    throw new functions.https.HttpsError("internal", "Could not enqueue task.", error);
  }
});


export const processTaskQueue = functions.https.onRequest(async (req, res) => {
  // Secure this function (e.g., check X-CloudScheduler header or a secret)
  // For now, public for testing.
  logger.info("processTaskQueue triggered.");

  try {
    const now = admin.firestore.Timestamp.now();
    const query = db.collection(TASKS_COLLECTION)
      .where("status", "==", "pending")
      .where("scheduled_for", "<=", now)
      .orderBy("priority", "desc")
      .orderBy("scheduled_for", "asc")
      .limit(1); // Process one task at a time to start

    const snapshot = await query.get();

    if (snapshot.empty) {
      logger.info("No pending tasks to process.");
      res.status(200).send("No pending tasks.");
      return;
    }

    const taskDoc = snapshot.docs[0];
    const taskId = taskDoc.id;
    // const taskDataOriginal = taskDoc.data(); // Renamed to avoid conflict with TaskData interface

    logger.info(`Attempting to process task: ${taskId}`, taskDoc.data());

    // Atomically update status to 'processing'
    await db.runTransaction(async (transaction) => {
      const freshTaskDoc = await transaction.get(db.collection(TASKS_COLLECTION).doc(taskId));
      if (!freshTaskDoc.exists || freshTaskDoc.data()?.status !== "pending") {
        throw new Error("Task is no longer pending or does not exist.");
      }
      transaction.update(db.collection(TASKS_COLLECTION).doc(taskId), {
        status: "processing",
        started_at: admin.firestore.FieldValue.serverTimestamp()
      });
    });

    // --- Start of new logic ---
    const taskDataFromDb = taskDoc.data() as TaskData; // Cast to known interface (defined in this file)
    logger.info(`Task ${taskId} status updated to processing. Original task data from DB:`, taskDataFromDb);

    let workResult: SubmissionResult | VerificationResult | { success: boolean; message: string; details?: any };

    try {
      // 1. Fetch related documents
      const platformDoc = await db.collection(PLATFORMS_COLLECTION).doc(taskDataFromDb.platform_id).get();
      if (!platformDoc.exists) {
        throw new Error(`Platform document ${taskDataFromDb.platform_id} not found for task ${taskId}.`);
      }
      const platformDetails = platformDoc.data()!;

      const campaignDoc = await db.collection(CAMPAIGNS_COLLECTION).doc(taskDataFromDb.campaign_id).get();
      if (!campaignDoc.exists) {
        throw new Error(`Campaign document ${taskDataFromDb.campaign_id} not found for task ${taskId}.`);
      }
      const campaignDetails = campaignDoc.data()!;

      const accountDetailsPlaceholder = { username: "dummyUser", password: "dummyPassword" };

      // 2. Prepare TaskPayload
      const anchorTextForTask = Array.isArray(campaignDetails.anchor_text) && campaignDetails.anchor_text.length > 0
                                ? campaignDetails.anchor_text[0]
                                : typeof campaignDetails.anchor_text === 'string' ? campaignDetails.anchor_text : "default anchor";

      const payload: TaskPayload = { // This TaskPayload is from ../handlers/base.ts
        id: taskId,
        campaign_id: taskDataFromDb.campaign_id,
        platform_id: taskDataFromDb.platform_id,
        backlink_id: taskDataFromDb.backlink_id || null,
        task_type: taskDataFromDb.task_type, // Already 'submission' | 'verification'
        target_url: campaignDetails.target_url,
        anchor_text: anchorTextForTask,
        keywords: campaignDetails.keywords || [],
        account_details: accountDetailsPlaceholder,
        platform_details: platformDetails,
        // content_template: {} // This would be fetched and processed if needed
      };

      // 3. Get handler and execute task
      const handler = PlatformHandlerFactory.getHandler(platformDetails.platform_type);

      if (payload.task_type === 'submission') {
        logger.info(`Executing SUBMISSION task ${taskId} with handler for platform type ${platformDetails.platform_type}`);
        workResult = await handler.submitBacklink(payload);
      } else if (payload.task_type === 'verification') {
        logger.info(`Executing VERIFICATION task ${taskId} with handler for platform type ${platformDetails.platform_type}`);
        workResult = await handler.verifyBacklink(payload);
      } else {
        throw new Error(`Unknown task_type: ${payload.task_type} for task ${taskId}`);
      }

      logger.info(`Task ${taskId} (type: ${payload.task_type}) processed by handler. Result:`, workResult);

    } catch (handlerError: any) {
      logger.error(`Error during platform handler execution for task ${taskId}:`, handlerError);
      workResult = {
        success: false,
        message: `Handler error: ${handlerError.message || 'Unknown error'}`,
        details: handlerError.stack, // Include stack for debugging
      };
    }

    // Update task to completed or failed based on workResult
    await db.collection(TASKS_COLLECTION).doc(taskId).update({
      status: workResult.success ? "completed" : "failed",
      completed_at: admin.firestore.FieldValue.serverTimestamp(),
      result: workResult // Store the detailed result from the handler
    });

    logger.info(`Task ${taskId} processing finished. Status: ${workResult.success ? 'completed' : 'failed'}.`);
    res.status(200).send(`Processed task ${taskId}. Result: ${workResult.message}`);
    // --- End of new logic ---

  } catch (error: any) {
    logger.error("Error in processTaskQueue:", error);
    if (error.message === "Task is no longer pending or does not exist.") {
        res.status(200).send("Task already processed by another worker or status changed.");
    } else {
        res.status(500).send(`Error processing task queue: ${error.message}`);
    }
  }
});

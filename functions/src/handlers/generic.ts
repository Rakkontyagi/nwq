import { PlatformHandler, TaskPayload, SubmissionResult, VerificationResult } from "./base";
import * as functions from "firebase-functions";

const logger = functions.logger;

export class GenericPlatformHandler implements PlatformHandler {
  async submitBacklink(task: TaskPayload): Promise<SubmissionResult> {
    logger.warn(`GenericPlatformHandler: submitBacklink called for platform type '${task.platform_details?.platform_type || 'unknown'}' (Task ID: ${task.id}). This platform type is not specifically supported yet.`);
    // Simulate a failure or a specific "not implemented" status
    return {
      success: false,
      message: `Submission not implemented for platform type: ${task.platform_details?.platform_type || 'unknown'}.`,
      details: { note: "This is a generic fallback handler." }
    };
  }

  async verifyBacklink(task: TaskPayload): Promise<VerificationResult> {
    logger.warn(`GenericPlatformHandler: verifyBacklink called for platform type '${task.platform_details?.platform_type || 'unknown'}' (Task ID: ${task.id}). This platform type is not specifically supported yet.`);
    // Simulate a failure or a specific "not implemented" status
    return {
      success: false,
      message: `Verification not implemented for platform type: ${task.platform_details?.platform_type || 'unknown'}.`,
      link_found: false, // Explicitly state link not found for verification
      details: { note: "This is a generic fallback handler." }
    };
  }
}

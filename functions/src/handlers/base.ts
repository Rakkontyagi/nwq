import * as admin from "firebase-admin";

// Define the structure of task data that handlers will receive.
// This might evolve but should contain essential details.
export interface TaskPayload {
  id: string; // Task ID
  campaign_id: string;
  platform_id: string;
  backlink_id?: string | null;
  task_type: 'submission' | 'verification';
  target_url: string; // From Campaign
  anchor_text: string; // Specific anchor text for this task (could be one from an array)
  keywords?: string[]; // From Campaign
  content_template?: any; // Processed content if needed for submission
  account_details?: any; // Account (username/password/cookies) to use for this task
  platform_details: any; // Details of the platform itself (URL, type, etc.)
}

export interface SubmissionResult {
  success: boolean;
  message: string;
  source_url?: string; // URL where the backlink was actually placed
  http_status?: number; // HTTP status when checking the source_url (if applicable)
  details?: any; // Any additional details from the submission process
}

export interface VerificationResult {
  success: boolean; // True if the link is found and valid
  message: string;
  status_code?: number; // HTTP status of the source_url
  link_found?: boolean;
  nofollow_status?: boolean | null; // True if nofollow, false if follow, null if not determined
  details?: any;
}

export interface PlatformHandler {
  submitBacklink(task: TaskPayload): Promise<SubmissionResult>;
  verifyBacklink(task: TaskPayload): Promise<VerificationResult>;
}

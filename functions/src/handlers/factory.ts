import { PlatformHandler } from "./base";
import { GenericPlatformHandler } from "./generic";
import { ProfilePlatformHandler } from "./profile"; // Import ProfilePlatformHandler
import * as functions from "firebase-functions";

const logger = functions.logger;

export class PlatformHandlerFactory {
  static getHandler(platformType: string): PlatformHandler {
    logger.info(`PlatformHandlerFactory: Getting handler for platform type: ${platformType}`);
    switch (platformType) {
      case "profile": // Add this case
        logger.info("Using ProfilePlatformHandler.");
        return new ProfilePlatformHandler();
      // case "wordpress_com":
      //   return new WordPressComHandler();
      default:
        logger.warn(`No specific handler found for platform type: ${platformType}. Using GenericPlatformHandler.`);
        return new GenericPlatformHandler();
    }
  }
}

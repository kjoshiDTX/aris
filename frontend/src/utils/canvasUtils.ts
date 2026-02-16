import { exportToBlob } from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';

export type CaptureQuality = 'high' | 'low';

/**
 * Captures the current state of the Excalidraw canvas as a Base64 string.
 * @param api - The Excalidraw API instance
 * @param quality - 'high' for manual analysis, 'low' for passive/debounce analysis
 * @returns Base64 encoded image string
 */
export async function captureCanvas(
    api: ExcalidrawImperativeAPI,
    quality: CaptureQuality
): Promise<string> {
    const elements = api.getSceneElements();
    const appState = api.getAppState();

    // Skip if canvas is empty
    if (elements.length === 0) {
        return '';
    }

    const config = quality === 'high'
        ? { maxWidthOrHeight: 2048, quality: 0.95 }
        : { maxWidthOrHeight: 512, quality: 0.7 };

    try {
        const blob = await exportToBlob({
            elements,
            appState: {
                ...appState,
                exportWithDarkMode: true,
                exportBackground: true,
            },
            files: api.getFiles(),
            mimeType: 'image/png',
            ...config,
        });

        return blobToBase64(blob);
    } catch (error) {
        console.error('Failed to capture canvas:', error);
        return '';
    }
}

/**
 * Converts a Blob to a Base64 string.
 * @param blob - The blob to convert
 * @returns Promise resolving to Base64 string (without data URI prefix)
 */
export function blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const result = reader.result as string;
            // Remove the data URI prefix (e.g., "data:image/png;base64,")
            const base64 = result.split(',')[1] || '';
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

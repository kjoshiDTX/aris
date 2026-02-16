import { useState, useEffect } from 'react';

/**
 * Custom hook that returns a debounced value.
 * The returned value only updates after the specified delay
 * has passed since the last change.
 * 
 * @param value - The value to debounce
 * @param delay - Delay in milliseconds (default: 5000ms for passive analysis)
 * @returns The debounced value
 */
export function useDebounce<T>(value: T, delay: number = 5000): T {
    const [debouncedValue, setDebouncedValue] = useState<T>(value);

    useEffect(() => {
        // Set up the timer
        const timer = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        // Clean up timer on value change or unmount
        return () => {
            clearTimeout(timer);
        };
    }, [value, delay]);

    return debouncedValue;
}

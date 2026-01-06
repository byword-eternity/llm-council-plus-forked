import { useState, useEffect } from 'react';

export default function StageTimer({ startTime, endTime, label = "Elapsed" }) {
    const [elapsed, setElapsed] = useState(0);

    useEffect(() => {
        if (!startTime) return;

        if (endTime) {
            // Final duration - timer is complete
            setElapsed(endTime - startTime);
            return;
        }

        // Active timer
        const interval = setInterval(() => {
            setElapsed(Date.now() - startTime);
        }, 100); // Update every 100ms for smoothness

        return () => clearInterval(interval);
    }, [startTime, endTime]);

    if (!startTime) return null;

    const formatTime = (ms) => {
        const seconds = (ms / 1000).toFixed(1);
        return `${seconds}s`;
    };

    const isComplete = !!endTime;

    return (
        <span className="stage-timer" style={{
            marginLeft: '10px',
            fontSize: '12px',
            fontFamily: 'monospace',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            color: isComplete ? '#22c55e' : '#666', // Green when complete, gray when running
            transition: 'color 0.3s ease'
        }}>
            {isComplete ? (
                <>
                    <span style={{ fontSize: '10px' }}>✓</span>
                    <span>{label}: {formatTime(elapsed)}</span>
                </>
            ) : (
                <span>{label}: {formatTime(elapsed)}</span>
            )}
        </span>
    );
}

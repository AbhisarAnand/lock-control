import React, { useState, useEffect } from "react";
import { useTracker } from "meteor/react-meteor-data";
import { Locks } from "/imports/api/locks";

export const LockControl = () => {
    const { locks, isLoading } = useTracker(() => {
        const sub = Meteor.subscribe("locks");
        return {
            locks: Locks.find().fetch(),
            isLoading: !sub.ready(),
        };
    });

    if (isLoading) return <p className="text-gray-500 text-center">Loading...</p>;

    return (
        <div className="lock-container">
            {locks.map((lock) => (
                <LockCard key={lock._id} lock={lock} />
            ))}
        </div>
    );
};

const LockCard = ({ lock }) => {
    const [timeSinceLastSeen, setTimeSinceLastSeen] = useState("Just now");
    const [isOnline, setIsOnline] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [newName, setNewName] = useState(lock.name);

    // Compute time since last seen
    useEffect(() => {
        const interval = setInterval(() => {
            const now = new Date();
            const lastSeen = new Date(lock.lastSeen);
            const diff = Math.floor((now - lastSeen) / 1000);

            setIsOnline(diff <= 10);
            setTimeSinceLastSeen(
                diff < 60 ? `${diff} sec ago` : `${Math.floor(diff / 60)} min ago`
            );
        }, 1000);

        return () => clearInterval(interval);
    }, [lock.lastSeen]);

    // Send Lock/Unlock Command
    const toggleLock = () => {
        const newCommand = lock.status === "LOCK" ? "UNLOCK" : "LOCK";
        Meteor.call("locks.sendCommand", lock.macAddress, newCommand, (error) => {
            if (error) console.error("❌ Command failed:", error);
        });
    };

    // Edit Lock Name
    const saveEdit = () => {
        Meteor.call("locks.updateLockName", lock.macAddress, newName);
        setIsEditing(false);
    };

    // Remove Lock
    const removeLock = () => {
        Meteor.call("locks.removeLock", lock.macAddress);
        setIsEditing(false);
    };

    return (
        <div className="lock-card">
            {/* Status Indicator */}
            <div className="status-row">
                <span className={`status-indicator ${isOnline ? "online" : "offline"}`}></span>
                <span className="lock-status">
                    {isOnline ? "Active" : `Disconnected (${timeSinceLastSeen})`}
                </span>
            </div>

            {/* Lock Name */}
            <h2 className="lock-name">{lock.name}</h2>

            {/* Lock Status & Toggle Button */}
            <button
                onClick={toggleLock}
                className={`lock-button ${isOnline ? (lock.status === "LOCK" ? "locked" : "unlocked") : "disabled"}`}
                disabled={!isOnline}
            >
                {lock.status === "LOCK" ? "🔓 Unlock" : "🔒 Lock"}
            </button>

            {/* Edit Button */}
            <button className="edit-button" onClick={() => setIsEditing(true)}>✏️ Edit</button>

            {/* Edit Modal */}
            {isEditing && (
                <div className="modal">
                    <div className="modal-content">
                        <h3>Edit Lock</h3>
                        <input
                            type="text"
                            className="edit-input"
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                        />
                        <div className="modal-actions">
                            <button onClick={saveEdit} className="save-button">Save</button>
                            <button onClick={removeLock} className="remove-button">Remove Lock</button>
                            <button onClick={() => setIsEditing(false)} className="cancel-button">Cancel</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
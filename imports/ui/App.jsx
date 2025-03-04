import React from "react";
import { LockControl } from "./LockControl";

export const App = () => (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-6 font-inter">
        <div className="bg-white shadow-lg rounded-lg p-6 w-full max-w-4xl">
            <h1 className="text-3xl font-bold text-gray-800 mb-6 text-center font-poppins">🔒 Lock Control Panel</h1>
            <LockControl />
        </div>
    </div>
);
import React from 'react';
import { createRoot } from 'react-dom/client';
import { Meteor } from 'meteor/meteor';
import { App } from '/imports/ui/App';

import "/client/main.css";

Meteor.startup(() => {
  const container = document.getElementById('root');
  if (!container) {
    console.error("🚨 Root container not found in the HTML file!");
    return;
  }
  const root = createRoot(container);
  root.render(<App />);
});
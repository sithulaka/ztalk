import React from 'react';
import Layout from '../components/Layout';

const Settings: React.FC = () => {
  return (
    <Layout title="Settings">
      <div className="space-y-6">
        <h2 className="text-xl font-semibold">Settings</h2>
        <p>Configure application settings and preferences.</p>
      </div>
    </Layout>
  );
};

export default Settings; 
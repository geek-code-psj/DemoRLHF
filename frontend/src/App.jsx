import React, { useState, useEffect } from 'react';

const API_BASE = "https://demorlhf.onrender.com";

const StatBox = ({ label, value }) => (
    <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{label}</div>
        <div style={{ fontSize: '1.1rem', fontWeight: '800' }}>{value}</div>
    </div>
);

const Header = ({ stats, onRefresh }) => (
    <header className="dashboard-header">
        <div>
            <h1 className="neon-text" style={{ fontSize: '1.5rem', marginBottom: '2px' }}>Dashboard</h1>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Evaluation Dashboard</div>
        </div>
        <div className="glass-card" style={{ padding: '8px 20px', display: 'flex', alignItems: 'center', gap: '20px' }}>
            <StatBox label="Executed" value={stats.total_executions} />
            <StatBox label="Total Prompts" value={stats.total_prompts} />
            <button className="btn btn-outline" style={{ padding: '6px 14px', fontSize: '0.75rem' }} onClick={onRefresh}>Sync</button>
        </div>
    </header>
);

const AddPrompt = ({ onPromptAdded }) => {
    const [text, setText] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!text.trim()) return;
        setIsSubmitting(true);
        try {
            const res = await fetch(`${API_BASE}/prompts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            if (res.ok) {
                setText("");
                onPromptAdded();
            } else {
                throw new Error("Failed to add prompt");
            }
        } catch (err) {
            alert("Error: Could not add prompt.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <section className="prompt-section glass-card" style={{ marginTop: '2rem' }}>
            <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <input
                    type="text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Enter a new prompt..."
                    style={{ flexGrow: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid #444', borderRadius: '6px', padding: '12px', color: '#fff', fontSize: '0.9rem' }}
                    disabled={isSubmitting}
                />
                <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                    {isSubmitting ? 'Adding...' : 'Add Prompt'}
                </button>
            </form>
        </section>
    );
};

const PromptList = ({ prompts, onSelectPrompt, onDeletePrompt, onExecutePrompt }) => (
    <div className="glass-card" style={{ marginTop: '2rem', padding: '1rem' }}>
        <h2 className="neon-text">Prompts</h2>
        <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem' }}>
            {prompts.map(p => (
                <li key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.8rem 0.5rem', borderBottom: '1px solid #333' }}>
                    <span style={{ flexGrow: 1 }}>{p.text}</span>
                    <div style={{ display: 'flex', gap: '10px' }}>
                       <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{p.execution_result ? 'Executed' : 'Not Executed'}</span>
                       <button className="btn btn-secondary" onClick={() => onSelectPrompt(p.id)}>View</button>
                       <button className="btn btn-primary" onClick={() => onExecutePrompt(p.id)}>Execute</button>
                       <button className="btn btn-outline" style={{color: '#ff6b6b'}} onClick={() => onDeletePrompt(p.id)}>Delete</button>
                    </div>
                </li>
            ))}
        </ul>
    </div>
);

const ExecutionResultView = ({ result }) => {
    if (!result) return <div className="neon-text">This prompt has not been executed yet.</div>;

    return (
        <div className="glass-card" style={{ padding: '1rem', marginTop: '1rem' }}>
            <h3 className="neon-text">Execution Result</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                    <h4>STDOUT</h4>
                    <pre style={{ background: '#111', padding: '0.5rem', borderRadius: '4px', whiteSpace: 'pre-wrap' }}>{result.stdout || 'empty'}</pre>
                </div>
                <div>
                    <h4>STDERR</h4>
                    <pre style={{ background: '#111', padding: '0.5rem', borderRadius: '4px', color: '#ff6b6b', whiteSpace: 'pre-wrap' }}>{result.stderr || 'empty'}</pre>
                </div>
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <StatBox label="Exit Code" value={result.exit_code} />
                <StatBox label="Tests Passed" value={result.tests_passed} />
                <StatBox label="Tests Failed" value={result.tests_failed} />
            </div>
        </div>
    );
};

function App() {
    const [prompts, setPrompts] = useState([]);
    const [stats, setStats] = useState({ total_prompts: 0, total_executions: 0 });
    const [loading, setLoading] = useState(true);
    const [selectedPrompt, setSelectedPrompt] = useState(null);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [promptsRes, statsRes] = await Promise.all([
                fetch(`${API_BASE}/prompts`),
                fetch(`${API_BASE}/stats`)
            ]);
            const promptsData = await promptsRes.json();
            const statsData = await statsRes.json();
            setPrompts(promptsData);
            setStats(statsData);
        } catch (err) {
            console.error("Failed to fetch data", err);
        } finally {
            setLoading(false);
        }
    };

    const handlePromptAdded = () => {
        fetchData();
    };

    const handleDeletePrompt = async (promptId) => {
        if (window.confirm("Are you sure you want to delete this prompt?")) {
            try {
                await fetch(`${API_BASE}/prompts/${promptId}`, { method: 'DELETE' });
                fetchData();
            } catch (err) {
                alert("Could not delete the prompt.");
            }
        }
    };

    const handleExecutePrompt = async (promptId) => {
        try {
            await fetch(`${API_BASE}/execute/${promptId}`, { method: 'POST' });
            fetchData();
        } catch (err) {
            alert("Could not execute the prompt.");
        }
    };

    useEffect(() => { fetchData(); }, []);

    if (loading && !prompts.length) return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
            <div className="neon-text" style={{ fontSize: '2rem' }}>Connecting to Pipeline...</div>
        </div>
    );

    if (selectedPrompt) {
        return (
            <div className="dashboard">
                 <Header stats={stats} onRefresh={fetchData} />
                 <button className="btn btn-outline" onClick={() => setSelectedPrompt(null)} style={{margin: '2rem 0'}}>← Back to List</button>
                 <h2 className="neon-text">{selectedPrompt.text}</h2>
                 <ExecutionResultView result={selectedPrompt.execution_result} />
            </div>
        )
    }

    return (
        <div className="dashboard">
            <Header stats={stats} onRefresh={fetchData} />
            <AddPrompt onPromptAdded={handlePromptAdded} />
            {loading && <div style={{textAlign: 'center', padding: '2rem'}}>Refreshing...</div>}
            {!loading && prompts.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    <h2 className="neon-text">No Prompts Found</h2>
                    <p>Get started by adding your first prompt above.</p>
                </div>
            ) : (
                <PromptList prompts={prompts} onSelectPrompt={(id) => setSelectedPrompt(prompts.find(p=>p.id === id))} onDeletePrompt={handleDeletePrompt} onExecutePrompt={handleExecutePrompt} />
            )}
        </div>
    );
}

export default App;

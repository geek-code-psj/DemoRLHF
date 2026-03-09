import React, { useState, useEffect } from 'react';

const API_BASE = "https://demorlhf.onrender.com";

// ── Helpers ────────────────────────────────────────────────────────────────────

function TestBadge({ result, loading }) {
    if (loading) return (
        <span style={badgeStyle('#333', '#aaa')}>⏳ Running tests...</span>
    );
    if (!result) return (
        <span style={badgeStyle('#1a1a2e', '#666')}>⚪ Not Executed</span>
    );
    if (result.timed_out) return (
        <span style={badgeStyle('#2d1b00', '#f5a623')}>⏱ Timed Out</span>
    );
    if (result.tests_error > 0 && result.tests_passed === 0) return (
        <span style={badgeStyle('#1a0a0a', '#ff6b6b')}>🔴 Error in Tests</span>
    );
    if (result.tests_failed > 0) return (
        <span style={badgeStyle('#1a0a0a', '#ff6b6b')}>
            🔴 {result.tests_failed} failed / {result.tests_passed} passed
        </span>
    );
    return (
        <span style={badgeStyle('#0a1a0a', '#39ff14')}>
            🟢 {result.tests_passed} tests passed
        </span>
    );
}

function badgeStyle(bg, color) {
    return {
        padding: '4px 10px',
        borderRadius: '6px',
        fontSize: '0.75rem',
        fontWeight: '600',
        background: bg,
        color: color,
        border: `1px solid ${color}40`,
        display: 'inline-block'
    };
}

// ── Main App ──────────────────────────────────────────────────────────────────

function App() {
    const [prompt, setPrompt] = useState(null);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState({ total_prompts: 0, total_ratings: 0, total_executions: 0 });
    const [execResults, setExecResults] = useState({});   // { [responseId]: result|null }
    const [execLoading, setExecLoading] = useState({});   // { [responseId]: bool }
    const [showOutput, setShowOutput] = useState({});     // { [responseId]: bool }
    const [showAddPrompt, setShowAddPrompt] = useState(false);
    const [newPromptText, setNewPromptText] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [history, setHistory] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);


    const fetchNext = async () => {
        setLoading(true);
        setExecResults({});
        setShowOutput({});
        try {
            const [promptRes, statsRes] = await Promise.all([
                fetch(`${API_BASE}/prompts/next`),
                fetch(`${API_BASE}/stats`)
            ]);
            const promptData = await promptRes.json();
            const statsData = await statsRes.json();
            setPrompt(promptData);
            setStats(statsData);

            // Load any existing execution results
            if (promptData?.responses) {
                const results = {};
                await Promise.all(promptData.responses.map(async (resp) => {
                    const r = await fetch(`${API_BASE}/results/${resp.id}`);
                    results[resp.id] = r.ok ? await r.json() : null;
                }));
                setExecResults(results);
            }
        } catch (err) {
            console.error("Failed to fetch prompt", err);
        } finally {
            setLoading(false);
        }
    };

    const runTests = async (responseId) => {
        setExecLoading(prev => ({ ...prev, [responseId]: true }));
        try {
            const res = await fetch(`${API_BASE}/execute/${responseId}`, { method: 'POST' });
            const data = await res.json();
            setExecResults(prev => ({ ...prev, [responseId]: data }));
        } catch (err) {
            console.error("Execution failed", err);
        } finally {
            setExecLoading(prev => ({ ...prev, [responseId]: false }));
        }
    };

    const submitRating = async (responseId, score) => {
        try {
            await fetch(`${API_BASE}/ratings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ response_id: responseId, score })
            });
            fetchNext();
        } catch (err) {
            console.error("Failed to submit rating", err);
        }
    };

    const handleAddPrompt = async () => {
        if (!newPromptText.trim()) return;
        setIsSubmitting(true);
        try {
            await fetch(`${API_BASE}/prompts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: newPromptText })
            });
            setNewPromptText("");
            setShowAddPrompt(false);
            fetchNext(); // Refresh to get a new prompt
        } catch (err) {
            console.error("Failed to add prompt", err);
            alert("Error adding prompt. See console for details.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const fetchHistory = async () => {
        setHistoryLoading(true);
        try {
            const res = await fetch(`${API_BASE}/prompts/all`); // Assuming this endpoint exists
            const data = await res.json();
            setHistory(data);
        } catch (err) {
            console.error("Failed to fetch history", err);
        } finally {
            setHistoryLoading(false);
        }
    };

    const handleShowHistory = () => {
        setShowHistory(true);
        fetchHistory();
    }


    useEffect(() => { fetchNext(); }, []);

    if (loading) return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
            <div className="neon-text" style={{ fontSize: '2rem' }}>Initializing AI Pipeline...</div>
        </div>
    );

    if (!prompt) return (
        <div style={{ padding: '40px', textAlign: 'center' }}>
            <h1 className="neon-text">All caught up!</h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: '20px' }}>No more prompts to rank right now.</p>
            <button className="btn btn-primary" style={{ margin: '20px auto', display: 'block' }} onClick={fetchNext}>Refresh</button>
            <button className="btn btn-secondary" style={{ margin: '20px auto', display: 'block' }} onClick={() => setShowAddPrompt(true)}>+ Add New Prompt</button>
        </div>
    );

    return (
        <div className="dashboard">
            {/* ── Add Prompt Modal ─────────────────────────────────────────────── */}
            {showAddPrompt && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
                    <div className="glass-card" style={{ padding: '2rem', width: '90%', maxWidth: '600px' }}>
                        <h2 className="neon-text">Add New Prompt</h2>
                        <textarea
                            value={newPromptText}
                            onChange={(e) => setNewPromptText(e.target.value)}
                            placeholder="Enter the new prompt challenge here..."
                            style={{ width: '100%', minHeight: '150px', margin: '1rem 0', background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid #444', borderRadius: '8px', padding: '1rem', fontSize: '1rem' }}
                        />
                        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                            <button className="btn btn-outline" onClick={() => setShowAddPrompt(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleAddPrompt} disabled={isSubmitting}>
                                {isSubmitting ? 'Submitting...' : 'Submit Prompt'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
             {/* -- History Modal -- */}
             {showHistory && (
                 <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
                    <div className="glass-card" style={{ padding: '2rem', width: '90%', maxWidth: '800px', maxHeight: '80vh', overflowY: 'auto' }}>
                         <h2 className="neon-text">Prompt History</h2>
                         {historyLoading ? (
                             <p>Loading history...</p>
                         ) : (
                            <ul style={{listStyle: 'none', padding: 0}}>
                                {history.map(p => (
                                    <li key={p.id} style={{borderBottom: '1px solid #444', padding: '1rem 0'}}>
                                        <p>{p.text}</p>
                                        <small style={{color: 'var(--text-secondary)'}}>
                                            ID: {p.id}
                                        </small>
                                    </li>
                                ))}
                            </ul>
                         )}
                         <button className="btn btn-outline" onClick={() => setShowHistory(false)} style={{marginTop: '1rem'}}>Close</button>
                    </div>
                </div>
            )}

            {/* ── Header ─────────────────────────────────────────────────────────── */}
            <header className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 className="neon-text" style={{ fontSize: '1.5rem', marginBottom: '2px' }}>RLHF Pipeline</h1>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Human-in-the-loop Evaluation Dashboard</div>
                </div>
                <div style={{display: 'flex', alignItems: 'center', gap: '20px'}}>
                    <button className="btn btn-secondary" onClick={handleShowHistory}>History</button>
                    <button className="btn btn-primary" onClick={() => setShowAddPrompt(true)}>+ Add Prompt</button>
                    <div className="glass-card" style={{ padding: '8px 20px', display: 'flex', alignItems: 'center', gap: '20px' }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Ranked</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: '800' }}>{stats.total_ratings}</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Executed</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: '800' }}>{stats.total_executions}</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Total</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: '800' }}>{stats.total_prompts}</div>
                        </div>
                        <button className="btn btn-outline" style={{ padding: '6px 14px', fontSize: '0.75rem' }} onClick={fetchNext}>Sync</button>
                    </div>
                </div>
            </header>

            {/* ── Prompt ─────────────────────────────────────────────────────────── */}
            <section className="prompt-section">
                <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                    <span className="neon-text" style={{ fontSize: '0.7rem', padding: '5px 10px', background: 'rgba(0,0,0,0.4)', borderRadius: '6px', whiteSpace: 'nowrap' }}>CHALLENGE</span>
                    <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#e0e0e0' }}>{prompt.text}</p>
                </div>
            </section>

            {/* ── Split Screen ───────────────────────────────────────────────────── */}
            <main className="split-container">
                {prompt.responses.map((resp, idx) => {
                    const result = execResults[resp.id];
                    const isExecLoading = execLoading[resp.id];
                    const isOutputOpen = showOutput[resp.id];

                    return (
                        <div key={resp.id} className="model-column">
                            {/* Column header */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                                    <h3 className="neon-text" style={{ fontSize: '1.1rem' }}>Candidate {String.fromCharCode(65 + idx)}</h3>
                                    <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>{resp.model_name}</span>
                                </div>
                                <TestBadge result={result} loading={isExecLoading} />
                            </div>

                            {/* Code block */}
                            <div className="code-block">
                                <pre><code>{resp.content}</code></pre>
                            </div>

                            {/* Stdout/Stderr toggle */}
                            {result && (result.stdout || result.stderr) && (
                                <div style={{ marginBottom: '1rem' }}>
                                    <button
                                        onClick={() => setShowOutput(prev => ({ ...prev, [resp.id]: !isOutputOpen }))}
                                        className="btn btn-outline"
                                        style={{ padding: '6px 12px', fontSize: '0.7rem', width: '100%' }}
                                    >
                                        {isOutputOpen ? '▲ Hide Output' : '▼ Show Output'}
                                    </button>
                                    {isOutputOpen && (
                                        <div style={{ background: '#0d1117', borderRadius: '8px', padding: '12px', marginTop: '8px', fontSize: '0.75rem', fontFamily: 'Fira Code, monospace', color: result.tests_failed > 0 ? '#ff9999' : '#99ff99', maxHeight: '200px', overflowY: 'auto' }}>
                                            <pre>{result.stderr || result.stdout}</pre>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Actions */}
                            <div className="actions-bar">
                                <button
                                    className="btn btn-outline"
                                    style={{ flexGrow: 1, padding: '13px', fontSize: '0.8rem' }}
                                    onClick={() => runTests(resp.id)}
                                    disabled={isExecLoading}
                                >
                                    {isExecLoading ? '⏳' : '▶'} Run Tests
                                </button>
                                <button
                                    className="btn btn-primary"
                                    style={{ flexGrow: 3, padding: '13px', background: idx === 0 ? 'var(--neon-blue)' : 'var(--neon-purple)' }}
                                    onClick={() => submitRating(resp.id, 1)}
                                >
                                    ✓ Select {String.fromCharCode(65 + idx)}
                                </button>
                                <button
                                    className="btn btn-outline"
                                    style={{ flexGrow: 1, padding: '13px', fontSize: '0.8rem' }}
                                    onClick={() => submitRating(resp.id, 0)}
                                >
                                    ✗
                                </button>
                            </div>
                        </div>
                    );
                })}
            </main>
        </div>
    );
}

export default App;
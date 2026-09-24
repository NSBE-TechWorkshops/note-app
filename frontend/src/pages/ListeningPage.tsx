function ListeningCapsule() {
  return <div className="listening-capsule" aria-label="Listening"><i /><i /><i /><i /><i /><i /><i /></div>;
}

export function ListeningPage() {
  return <main className="reference-page">
    <button className="menu-button" aria-label="Open sidebar"><span /><span /><span /></button>
    <section className="state-center listening-state">
      <p className="state-question">Can you explain the notes I uploaded?</p>
      <small>Listening</small>
    </section>
    <ListeningCapsule />
  </main>;
}

import spinner from "../assets/corg/spinner.svg";

export function ThinkingPage() {
  return <main className="reference-page">
    <button className="menu-button" aria-label="Open sidebar"><span /><span /><span /></button>
    <section className="state-center thinking-state">
      <p className="state-question">Can you explain the notes I uploaded?</p>
      <p className="thinking-copy">Reading your uploaded material and finding the parts that best answer your question.</p>
    </section>
    <div className="thinking-pill reference-thinking"><img src={spinner} alt="Thinking" /></div>
  </main>;
}

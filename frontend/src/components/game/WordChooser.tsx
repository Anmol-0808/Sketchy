type Props = {
  options: string[];
  isDrawer: boolean;
  drawerName: string | null;
  onChoose: (word: string) => void;
};

export function WordChooser({ options, isDrawer, drawerName, onChoose }: Props) {
  return (
    <div className="word-chooser">
      {isDrawer ? (
        <>
          <h2>Choose a word</h2>
          <div className="word-options">
            {options.map((word) => (
              <button key={word} onClick={() => onChoose(word)}>
                {word}
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <h2>{drawerName || "The drawer"} is choosing</h2>
          <p>The round will begin as soon as a word is selected.</p>
        </>
      )}
    </div>
  );
}

import {Composition} from 'remotion';
import {Clip, calculateClipMetadata, FPS, HEIGHT, WIDTH} from './Clip';

// Клип выбирается через --props='{"name":"<имя файла из public/edits без .json>"}'
export const Root = () => (
	<Composition
		id="Clip"
		component={Clip}
		durationInFrames={1}
		fps={FPS}
		width={WIDTH}
		height={HEIGHT}
		defaultProps={{name: ''}}
		calculateMetadata={calculateClipMetadata}
	/>
);

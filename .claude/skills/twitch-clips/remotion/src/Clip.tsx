import React from 'react';
import {
	AbsoluteFill,
	CalculateMetadataFunction,
	OffthreadVideo,
	Sequence,
	staticFile,
	useCurrentFrame,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Montserrat';

// Вертикальный клип 9:16 (стиль в style.md навыка, параметры в config.json -> edit.style):
// сверху камера стримера, снизу контент, плашка Twitch + ник сверху по центру нижнего блока
// на стыке с камерой, белые субтитры капслоком с тире. Склейки встык, без переходов.

const {fontFamily} = loadFont('normal', {weights: ['900'], subsets: ['cyrillic', 'latin']});

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;
const SRC_W = 1920;
const SRC_H = 1080;

type Rect = [number, number, number, number];
type Piece = {src: string; from: number; to: number; cam?: Rect; content?: Rect; full?: Rect};
type Subtitle = {start: number; end: number; text: string};
type Style = {
	nickname: string;
	cam_height: number;
	subtitles: {font_weight: number; font_size: number; color: string; stroke_color: string; stroke_px: number; bottom_px: number};
	badge: {top_offset_px: number; font_size: number; stroke_px: number; icon_px: number};
};
type Edit = {name: string; duration: number; style: Style; pieces: Piece[]; subtitles: Subtitle[]};
export type ClipProps = {name: string; edit?: Edit};

const frames = (p: Piece) => Math.round((p.to - p.from) * FPS);

export const calculateClipMetadata: CalculateMetadataFunction<ClipProps> = async ({props}) => {
	const edit: Edit = await fetch(staticFile(`edits/${props.name}.json`)).then((r) => r.json());
	return {durationInFrames: edit.pieces.reduce((acc, p) => acc + frames(p), 0), props: {...props, edit}};
};

// Показывает область rect исходного кадра 1920x1080 в рамке boxW x boxH.
// Окно обрезается ровно по rect, чтобы соседние области экрана не попадали в кадр.
const Crop: React.FC<{
	piece: Piece;
	rect: Rect;
	boxW: number;
	boxH: number;
	fit: 'cover' | 'contain';
	muted?: boolean;
	filter?: string;
}> = ({piece, rect, boxW, boxH, fit, muted, filter}) => {
	const [x, y, w, h] = rect;
	const scale = fit === 'cover' ? Math.max(boxW / w, boxH / h) : Math.min(boxW / w, boxH / h);
	const winW = Math.min(boxW, w * scale);
	const winH = Math.min(boxH, h * scale);
	return (
		<div style={{position: 'absolute', left: (boxW - winW) / 2, top: (boxH - winH) / 2, width: winW, height: winH, overflow: 'hidden'}}>
			<OffthreadVideo
				src={staticFile(piece.src)}
				trimBefore={Math.round(piece.from * FPS)}
				trimAfter={Math.round(piece.to * FPS)}
				muted={muted}
				style={{
					position: 'absolute',
					width: SRC_W * scale,
					height: SRC_H * scale,
					left: (winW - w * scale) / 2 - x * scale,
					top: (winH - h * scale) / 2 - y * scale,
					maxWidth: 'none',
					filter,
				}}
			/>
		</div>
	);
};

const PieceView: React.FC<{piece: Piece; camH: number}> = ({piece, camH}) => {
	if (piece.full) {
		return (
			<AbsoluteFill style={{backgroundColor: 'black'}}>
				<Crop piece={piece} rect={piece.full} boxW={WIDTH} boxH={HEIGHT} fit="cover" />
			</AbsoluteFill>
		);
	}
	if (!piece.cam || !piece.content) return null;
	const contentH = HEIGHT - camH;
	return (
		<AbsoluteFill style={{backgroundColor: 'black'}}>
			<div style={{position: 'absolute', top: 0, left: 0, width: WIDTH, height: camH, overflow: 'hidden'}}>
				<Crop piece={piece} rect={piece.cam} boxW={WIDTH} boxH={camH} fit="cover" />
			</div>
			<div style={{position: 'absolute', top: camH, left: 0, width: WIDTH, height: contentH, overflow: 'hidden'}}>
				{/* размытая подложка заполняет поля, если контент уже кадра */}
				<Crop piece={piece} rect={piece.content} boxW={WIDTH} boxH={contentH} fit="cover" muted filter="blur(40px) brightness(0.55)" />
				<Crop piece={piece} rect={piece.content} boxW={WIDTH} boxH={contentH} fit="contain" muted />
			</div>
		</AbsoluteFill>
	);
};

const outline = (px: number, color = 'black'): React.CSSProperties => ({WebkitTextStroke: `${px}px ${color}`, paintOrder: 'stroke fill'});

const Badge: React.FC<{style: Style}> = ({style}) => {
	const b = style.badge;
	return (
		<div
			style={{
				position: 'absolute',
				top: style.cam_height + b.top_offset_px,
				left: 0,
				right: 0,
				display: 'flex',
				justifyContent: 'center',
				alignItems: 'center',
				gap: 14,
			}}
		>
			<div style={{background: '#9146FF', borderRadius: 12, padding: 9, display: 'flex', boxShadow: '0 0 0 4px black'}}>
				<svg width={b.icon_px} height={b.icon_px} viewBox="0 0 24 24">
					<path
						fill="white"
						d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z"
					/>
				</svg>
			</div>
			<div style={{fontFamily, fontWeight: 900, fontSize: b.font_size, color: 'white', ...outline(b.stroke_px)}}>{style.nickname}</div>
		</div>
	);
};

const Subtitles: React.FC<{subs: Subtitle[]; style: Style}> = ({subs, style}) => {
	const t = useCurrentFrame() / FPS;
	const cur = subs.find((s) => t >= s.start && t < s.end);
	if (!cur) return null;
	const s = style.subtitles;
	return (
		<div
			style={{
				position: 'absolute',
				left: 60,
				right: 60,
				bottom: s.bottom_px,
				textAlign: 'center',
				fontFamily,
				fontWeight: s.font_weight,
				fontSize: s.font_size,
				lineHeight: 1.1,
				color: s.color,
				...outline(s.stroke_px, s.stroke_color),
			}}
		>
			{cur.text}
		</div>
	);
};

export const Clip: React.FC<ClipProps> = ({edit}) => {
	if (!edit) return null;
	let at = 0;
	return (
		<AbsoluteFill style={{backgroundColor: 'black'}}>
			{edit.pieces.map((p, i) => {
				const from = at;
				at += frames(p);
				return (
					<Sequence key={i} from={from} durationInFrames={frames(p)}>
						<PieceView piece={p} camH={edit.style.cam_height} />
					</Sequence>
				);
			})}
			<Badge style={edit.style} />
			<Subtitles subs={edit.subtitles} style={edit.style} />
		</AbsoluteFill>
	);
};

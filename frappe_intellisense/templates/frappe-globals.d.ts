interface Window {
	frappe: Frappe;
	cur_frm: FrappeForm | null;
	cur_list: FrappeList | null;
}

declare const frappe: Frappe;
declare const cur_frm: FrappeForm | null;
declare const cur_list: FrappeList | null;
declare const locals: Record<string, Record<string, unknown>>;
declare const __: (message: string, ...replacements: unknown[]) => string;

interface FrappeCallOptions {
	method: string;
	args?: Record<string, unknown>;
	callback?: (response: { message: unknown }) => void;
	error?: (response: { message?: unknown }) => void;
	quiet?: boolean;
	no_spinner?: boolean;
	freeze?: boolean;
	json?: boolean;
}

interface Frappe {
	/** Create a namespace on the global object. */
	provide(namespace: string): Record<string, unknown>;

	/** Call a whitelisted server method. */
	call(options: FrappeCallOptions): void;

	/** Call a whitelisted server method and await its message. */
	xcall(
		method: string,
		params?: Record<string, unknown>,
		type?: string,
		options?: Record<string, unknown>
	): Promise<unknown>;

	/** Form and list view APIs. */
	ui: {
		form: {
			/** Register a handler for a DocType event or a field event. */
			on(
				doctype: string,
				fieldname: string | Record<string, (...args: unknown[]) => void>,
				handler?: (...args: unknown[]) => void
			): void;
			off(doctype: string, fieldname: string, handler?: (...args: unknown[]) => void): void;
		};
		[key: string]: unknown;
	};

	/** Client-side document helpers. */
	model: {
		set_value(
			doctype: string,
			name: string,
			fieldname: string | Record<string, unknown>,
			value?: unknown
		): void;
		get_doc(doctype: string, name?: string): Record<string, unknown>;
		[key: string]: unknown;
	};

	/** Show a message in the desk. */
	msgprint(message: string): void;

	/** Raise a desk error. */
	throw(message: string): void;

	new_doc(doctype: string, name?: string, callback?: (doc: Record<string, unknown>) => void): void;
	boot: Record<string, unknown>;
	lang: string;
	[key: string]: unknown;
}

interface FrappeForm {
	doc: Record<string, unknown>;
	doctype: string;
	name: string;
	is_new(): boolean;
	set_value(fieldname: string | Record<string, unknown>, value?: unknown): void;
	get_value(fieldname: string): unknown;
	refresh_field(fieldname: string | string[]): void;
	save(): Promise<unknown>;
	events: Record<string, (...args: unknown[]) => void>;
	[key: string]: unknown;
}

interface FrappeList {
	doctype: string;
	refresh(): void;
	[key: string]: unknown;
}

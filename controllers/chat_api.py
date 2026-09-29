import json
import logging
import odoo
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class AIChatController(http.Controller):

    @http.route('/api/ai/config', type='http', auth='public', methods=['GET'], csrf=False)
    def get_config(self, **kwargs):
        mode = request.env['ir.config_parameter'].sudo().get_param('odoo_ai_assistant.chat_ui_mode', 'both')
        return Response(json.dumps({'chat_ui_mode': mode}), content_type='application/json')

    @http.route('/api/ai/threads', type='http', auth='user', methods=['GET'], csrf=False)
    def get_threads(self, **kwargs):
        threads = request.env['ai.chat.thread'].search([('user_id', '=', request.env.user.id)], order='write_date desc')
        result = [{'id': t.id, 'title': t.name, 'updated_at': t.write_date.isoformat()} for t in threads]
        return Response(json.dumps(result), content_type='application/json')

    @http.route('/api/ai/threads', type='http', auth='user', methods=['POST'], csrf=False)
    def create_thread(self, **kwargs):
        data = json.loads(request.httprequest.data) if request.httprequest.data else {}
        title = data.get('title', 'แชทใหม่')
        thread = request.env['ai.chat.thread'].create({'name': title})
        request.env.cr.commit()
        return Response(json.dumps({'id': thread.id, 'title': thread.name}), content_type='application/json')

    @http.route('/api/ai/threads/<int:thread_id>', type='http', auth='user', methods=['PATCH'], csrf=False)
    def rename_thread(self, thread_id, **kwargs):
        thread = request.env['ai.chat.thread'].browse(thread_id)
        if thread.exists() and thread.user_id == request.env.user:
            data = json.loads(request.httprequest.data)
            thread.write({'name': data.get('title', thread.name)})
            request.env.cr.commit()
            return Response(json.dumps({'success': True}), content_type='application/json')
        return Response(json.dumps({'error': 'Not found or unauthorized'}), status=404, content_type='application/json')

    @http.route('/api/ai/threads/<int:thread_id>', type='http', auth='user', methods=['DELETE'], csrf=False)
    def delete_thread(self, thread_id, **kwargs):
        thread = request.env['ai.chat.thread'].browse(thread_id)
        if thread.exists() and thread.user_id == request.env.user:
            thread.unlink()
            request.env.cr.commit()
            return Response(json.dumps({'success': True}), content_type='application/json')
        return Response(json.dumps({'error': 'Not found or unauthorized'}), status=404, content_type='application/json')

    @http.route('/api/ai/threads/<int:thread_id>/messages', type='http', auth='user', methods=['GET'], csrf=False)
    def get_messages(self, thread_id, **kwargs):
        thread = request.env['ai.chat.thread'].browse(thread_id)
        if not thread.exists() or thread.user_id != request.env.user:
            return Response(json.dumps({'error': 'Unauthorized'}), status=403, content_type='application/json')
        
        messages = thread.message_ids
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'tool_calls': json.loads(msg.tool_calls) if msg.tool_calls else [],
                'tool_results': json.loads(msg.tool_results) if msg.tool_results else [],
                'thinking_steps': json.loads(msg.thinking_steps) if msg.thinking_steps else []
            })
        return Response(json.dumps(result), content_type='application/json')

    @http.route('/api/ai/chat', type='http', auth='user', methods=['POST'], csrf=False)
    def chat_stream(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            thread_id = data.get('thread_id')
            messages = data.get('messages', [])
            
            # 1. Setup thread
            thread = None
            if thread_id:
                try:
                    thread = request.env['ai.chat.thread'].browse(int(thread_id))
                    if not thread.exists() or thread.user_id != request.env.user:
                        thread = None
                except (ValueError, TypeError):
                    thread = None

            if not thread:
                title = 'แชทใหม่'
                if messages and messages[-1].get('role') == 'user':
                    first_text = (messages[-1].get('content') or '').strip()[:30]
                    if first_text:
                        title = first_text
                thread = request.env['ai.chat.thread'].create({'name': title})
                thread_id = thread.id
                
            # 2. Save user message to DB
            if messages and messages[-1].get('role') == 'user':
                request.env['ai.chat.message'].create({
                    'thread_id': thread.id,
                    'role': 'user',
                    'content': messages[-1].get('content', '')
                })

            # Explicitly commit thread and user message before streaming begins
            request.env.cr.commit()

            # Capture context before leaving the request thread/scope
            registry = request.env.registry
            uid = request.env.user.id
            context = dict(request.env.context)
            thread_saved_id = thread.id

            # 3. Stream Generator (runs independently during WSGI streaming)
            def generate():
                thinking_steps_log = []
                full_content = ""
                tool_calls_log = []
                
                # Send immediate ping to establish connection and prevent proxy/browser timeout
                yield ": ping\n\n"

                try:
                    with registry.cursor() as cr:
                        env = odoo.api.Environment(cr, uid, context)
                        for event in env['ai.engine'].chat_stream(messages):
                            # Log for persistence
                            if event['event'] == 'thinking':
                                thinking_steps_log.append({'type': 'thinking', 'text': event['data'].get('text', '')})
                            elif event['event'] == 'tool-call':
                                thinking_steps_log.append({
                                    'type': 'tool-call', 
                                    'name': event['data'].get('name'), 
                                    'args': event['data'].get('args')
                                })
                                tool_calls_log.append(event['data'])
                            elif event['event'] == 'tool-result':
                                thinking_steps_log.append({
                                    'type': 'tool-result', 
                                    'name': event['data'].get('name'), 
                                    'summary': event['data'].get('summary')
                                })
                            elif event['event'] == 'text-delta':
                                full_content += event['data'].get('text', '')
                            
                            # Add _event marker for frontend parsing
                            event['data']['_event'] = event['event']
                            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
                        
                        # 4. Save Assistant Response to DB after streaming completes
                        env['ai.chat.message'].create({
                            'thread_id': thread_saved_id,
                            'role': 'assistant',
                            'content': full_content,
                            'thinking_steps': json.dumps(thinking_steps_log),
                            'tool_calls': json.dumps(tool_calls_log)
                        })
                        cr.commit()
                        
                        yield f"event: done\ndata: {json.dumps({'thread_id': str(thread_saved_id)})}\n\n"
                except Exception as e:
                    _logger.exception("Streaming error")
                    error_data = {'_event': 'error', 'error': str(e)}
                    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

            return Response(
                generate(), 
                mimetype='text/event-stream',
                direct_passthrough=True,
                headers=[
                    ('Cache-Control', 'no-cache, no-transform'),
                    ('Connection', 'keep-alive'),
                    ('X-Accel-Buffering', 'no'),
                ]
            )
        except Exception as e:
            _logger.exception("Chat API Error")
            return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')


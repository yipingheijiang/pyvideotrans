import asyncio

import threading

import edge_tts

from videotrans.configure import config
from videotrans.tts._base import BaseTTS
from videotrans.util import tools

# asyncio 异步并发

class EdgeTTS(BaseTTS):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

    async def _item_task(self,data_item=None):
        split_queue=[self.queue_tts[i:i+self.dub_nums] for i in range(0,self.len,self.dub_nums)]
        try:
            for items in split_queue:
                tasks = []
                for it in items:
                    if not tools.vail_file(it['filename']):
                        communicate_task = edge_tts.Communicate(
                            text=it["text"], voice=it['role'],rate=self.rate,volume=self.volume,pitch=self.pitch)
                        tasks.append(communicate_task.save(it['filename']))
                        print(f'开始 {it["text"]}')
                if len(tasks)<1:
                    continue
                # 使用 asyncio.gather 并行执行保存任务
                await asyncio.gather(*tasks)
                self.has_done+=self.dub_nums
                if self.inst and self.inst.precent < 80:
                    self.inst.precent += 0.1
                tools.set_process(f'{config.transobj["kaishipeiyin"]} [{self.has_done}/{self.len}]', type="logs", uuid=self.uuid)
        except Exception as e:
            self.error=str(e)
            tools.set_process(f'{str(e)}', type="logs", uuid=self.uuid)
            config.logger.exception(e,exc_info=True)

    def _exec(self) ->None:
        # 防止出错，重试一次
        for i in range(2):
            t=threading.Thread(target=self._run_as_async)
            t.start()
            t.join()
            nofile=0
            for it in self.queue_tts:
                if not tools.vail_file(it['filename']):
                    nofile+=1
                    break
            # 有错误则降低并发，重试
            if nofile>0:
                config.logger.error(f'存在失败的配音，重试')
                self.dub_nums=1
                self.has_done = 0
                self.error=''
            else:
                break
    def _run_as_async(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._item_task())
        finally:
            loop.close()
